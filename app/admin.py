from datetime import date, datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError

from .auth import current_user, require_admin
from .journal import log_admin
from .models import (
    AdminAction,
    PaymentType,
    Request,
    Status,
    User,
    WorkType,
    db,
    exists,
    tickets_select,
)
from .validators import validate_admin_ticket, validate_catalog_name, validate_status_record

bp = Blueprint("admin", __name__)

PER_PAGE = 5
JOURNAL_PER_PAGE = 10

CATALOGS = {
    "work-types": {
        "model": WorkType,
        "title": "Варианты работ",
        "one": "вариант работ",
        "entity": "work_type",
        "fk": Request.work_type_id,
        "order": WorkType.name,
        "fields": ("name",),
    },
    "payment-types": {
        "model": PaymentType,
        "title": "Способы оплаты",
        "one": "способ оплаты",
        "entity": "payment_type",
        "fk": Request.payment_type_id,
        "order": PaymentType.id,
        "fields": ("name",),
    },
    "statuses": {
        "model": Status,
        "title": "Статусы",
        "one": "статус",
        "entity": "status",
        "fk": Request.status_id,
        "order": Status.sort_order,
        "fields": ("code", "name", "sort_order"),
    },
}

ACTION_LABELS = {
    "login": "Вход",
    "create": "Создание",
    "update": "Изменение",
    "delete": "Удаление",
}
ENTITY_LABELS = {
    "request": "заявка",
    "work_type": "вариант работ",
    "payment_type": "оплата",
    "status": "статус",
    "user": "пользователь",
}


@bp.get("/admin")
@require_admin
def tickets():
    clauses, filters = _ticket_filters(request.args)
    count_stmt = (
        select(func.count())
        .select_from(Request)
        .join(User, User.id == Request.user_id)
        .join(WorkType, WorkType.id == Request.work_type_id)
        .join(Status, Status.id == Request.status_id)
    )
    list_stmt = tickets_select()
    if clauses:
        condition = and_(*clauses)
        count_stmt = count_stmt.where(condition)
        list_stmt = list_stmt.where(condition)
    total = db.session.execute(count_stmt).scalar_one()
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = request.args.get("page", 1, type=int) or 1
    page = min(max(page, 1), pages)
    offset = (page - 1) * PER_PAGE
    rows = db.session.execute(
        list_stmt.order_by(Request.created_at.desc(), Request.id.desc()).limit(PER_PAGE).offset(offset)
    ).all()
    return render_template(
        "admin.html",
        tickets=rows,
        statuses=db.session.execute(select(Status).order_by(Status.sort_order)).scalars().all(),
        work_types=db.session.execute(select(WorkType).order_by(WorkType.name)).scalars().all(),
        filters=filters,
        page=page,
        pages=pages,
        total=total,
    )


@bp.post("/admin/requests/<int:ticket_id>/status")
@require_admin
def set_status(ticket_id):
    user = current_user()
    status_id = request.form.get("status_id", type=int)
    ticket = db.session.get(Request, ticket_id)
    if not ticket:
        flash("Заявка не найдена.", "error")
    elif not status_id or not exists(Status, status_id):
        flash("Выберите статус из списка.", "error")
    else:
        ticket.status_id = status_id
        ticket.updated_at = datetime.now()
        log_admin(user, "update", "request", ticket.id, f"Заявка №{ticket.id}: смена статуса")
        db.session.commit()
        flash(f"Заявка №{ticket_id}: статус изменён.", "success")
    return redirect(_tickets_url())


@bp.route("/admin/requests/new", methods=["GET", "POST"])
@require_admin
def new_request():
    return _request_form(ticket=None)


@bp.route("/admin/requests/<int:ticket_id>/edit", methods=["GET", "POST"])
@require_admin
def edit_request(ticket_id):
    ticket = db.session.get(Request, ticket_id)
    if not ticket:
        abort(404)
    return _request_form(ticket)


@bp.route("/admin/requests/<int:ticket_id>/delete", methods=["GET", "POST"])
@require_admin
def delete_request(ticket_id):
    user = current_user()
    ticket = db.session.get(Request, ticket_id)
    if not ticket:
        abort(404)
    title = f"заявку №{ticket.id}"
    description = f"{ticket.address}, кв. {ticket.apartment}. Запись будет удалена без восстановления."
    if request.method == "POST":
        log_admin(user, "delete", "request", ticket.id, f"Заявка №{ticket.id}: {ticket.address}")
        db.session.delete(ticket)
        db.session.commit()
        flash(f"Заявка №{ticket_id} удалена.", "success")
        return redirect(url_for("admin.tickets"))
    return render_template(
        "admin_confirm_delete.html",
        title=title,
        description=description,
        cancel_url=url_for("admin.tickets"),
    )


@bp.get("/admin/catalogs")
@require_admin
def catalogs():
    groups = []
    for kind, spec in CATALOGS.items():
        items = db.session.execute(select(spec["model"]).order_by(spec["order"])).scalars().all()
        groups.append({"kind": kind, "spec": spec, "rows": items})
    return render_template("admin_catalogs.html", groups=groups)


@bp.route("/admin/catalogs/<kind>/new", methods=["GET", "POST"])
@require_admin
def new_catalog(kind):
    spec = _catalog(kind)
    return _catalog_form(kind, spec, item=None)


@bp.route("/admin/catalogs/<kind>/<int:item_id>/edit", methods=["GET", "POST"])
@require_admin
def edit_catalog(kind, item_id):
    spec = _catalog(kind)
    item = db.session.get(spec["model"], item_id)
    if not item:
        abort(404)
    return _catalog_form(kind, spec, item)


@bp.route("/admin/catalogs/<kind>/<int:item_id>/delete", methods=["GET", "POST"])
@require_admin
def delete_catalog(kind, item_id):
    user = current_user()
    spec = _catalog(kind)
    item = db.session.get(spec["model"], item_id)
    if not item:
        abort(404)
    used = db.session.execute(
        select(func.count()).select_from(Request).where(spec["fk"] == item.id)
    ).scalar_one()
    remaining = db.session.execute(select(func.count()).select_from(spec["model"])).scalar_one()
    label = getattr(item, "name", str(item.id))
    if used:
        flash(f"Нельзя удалить «{label}»: есть заявки с этой записью.", "error")
        return redirect(url_for("admin.catalogs"))
    if remaining <= 1:
        flash(f"Нужна хотя бы одна запись в справочнике «{spec['title']}».", "error")
        return redirect(url_for("admin.catalogs"))
    if request.method == "POST":
        log_admin(user, "delete", spec["entity"], item.id, f"{spec['title']}: {label}")
        db.session.delete(item)
        db.session.commit()
        flash(f"Запись «{label}» удалена.", "success")
        return redirect(url_for("admin.catalogs"))
    return render_template(
        "admin_confirm_delete.html",
        title=f"{spec['one']} «{label}»",
        description="Справочник изменится сразу. Заявки с этой записью отсутствуют.",
        cancel_url=url_for("admin.catalogs"),
    )


@bp.get("/admin/journal")
@require_admin
def journal():
    action = (request.args.get("action") or "").strip()
    stmt = select(AdminAction)
    count_stmt = select(func.count()).select_from(AdminAction)
    if action in ACTION_LABELS:
        stmt = stmt.where(AdminAction.action == action)
        count_stmt = count_stmt.where(AdminAction.action == action)
    total = db.session.execute(count_stmt).scalar_one()
    pages = max(1, (total + JOURNAL_PER_PAGE - 1) // JOURNAL_PER_PAGE)
    page = request.args.get("page", 1, type=int) or 1
    page = min(max(page, 1), pages)
    offset = (page - 1) * JOURNAL_PER_PAGE
    rows = db.session.execute(
        stmt.order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(JOURNAL_PER_PAGE)
        .offset(offset)
    ).scalars().all()
    return render_template(
        "admin_journal.html",
        rows=rows,
        action_labels=ACTION_LABELS,
        entity_labels=ENTITY_LABELS,
        filters={"action": action},
        page=page,
        pages=pages,
        total=total,
    )


def _catalog(kind):
    spec = CATALOGS.get(kind)
    if not spec:
        abort(404)
    return spec


def _catalog_form(kind, spec, item):
    user = current_user()
    creating = item is None
    errors = {}
    form = _catalog_values(spec, item)
    if request.method == "POST":
        if spec["fields"] == ("name",):
            errors, form = validate_catalog_name(request.form)
        else:
            errors, form = validate_status_record(request.form)
        if not errors:
            target = item or spec["model"]()
            for field in spec["fields"]:
                setattr(target, field, form[field])
            try:
                if creating:
                    db.session.add(target)
                db.session.flush()
                log_admin(
                    user,
                    "create" if creating else "update",
                    spec["entity"],
                    target.id,
                    f"{spec['title']}: {form.get('name') or getattr(target, 'name', target.id)}",
                )
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                errors["name"] = "Такое название, код или порядок уже заняты."
            else:
                flash("Запись сохранена." if creating else "Запись изменена.", "success")
                return redirect(url_for("admin.catalogs"))
    return render_template(
        "admin_catalog_form.html",
        spec=spec,
        kind=kind,
        form=form,
        errors=errors,
        creating=creating,
    ), (400 if errors else 200)


def _catalog_values(spec, item):
    values = {field: "" for field in spec["fields"]}
    if item is None:
        return values
    for field in spec["fields"]:
        value = getattr(item, field)
        values[field] = "" if value is None else str(value)
    return values


def _request_form(ticket):
    user = current_user()
    creating = ticket is None
    errors = {}
    form = _ticket_values(ticket)
    if request.method == "POST":
        errors, form = validate_admin_ticket(request.form)
        if not errors:
            if not exists(User, form["user_id"]) or db.session.get(User, form["user_id"]).role == "admin":
                errors["user_id"] = "Выберите абонента из списка."
            if not exists(WorkType, form["work_type_id"]):
                errors["work_type_id"] = "Выберите вариант работ."
            if not exists(PaymentType, form["payment_type_id"]):
                errors["payment_type_id"] = "Выберите способ оплаты."
            if not exists(Status, form["status_id"]):
                errors["status_id"] = "Выберите статус."
        if not errors:
            target = ticket or Request()
            target.user_id = form["user_id"]
            target.address = form["address"]
            target.apartment = form["apartment"]
            target.contact_phone = form["contact_phone"]
            target.problem = form["problem"]
            target.work_type_id = form["work_type_id"]
            target.visit_date = date.fromisoformat(form["visit_date"])
            target.payment_type_id = form["payment_type_id"]
            target.status_id = form["status_id"]
            if creating:
                db.session.add(target)
                db.session.flush()
                log_admin(user, "create", "request", target.id, f"Заявка №{target.id}: {target.address}")
                flash("Заявка создана.", "success")
            else:
                target.updated_at = datetime.now()
                log_admin(user, "update", "request", target.id, f"Заявка №{target.id}: {target.address}")
                flash(f"Заявка №{target.id} изменена.", "success")
            db.session.commit()
            return redirect(url_for("admin.tickets"))
    return render_template(
        "admin_request_form.html",
        errors=errors,
        form=form,
        creating=creating,
        ticket=ticket,
        subscribers=_subscribers(ticket),
        work_types=db.session.execute(select(WorkType).order_by(WorkType.name)).scalars().all(),
        payment_types=db.session.execute(select(PaymentType).order_by(PaymentType.id)).scalars().all(),
        statuses=db.session.execute(select(Status).order_by(Status.sort_order)).scalars().all(),
    ), (400 if errors else 200)


def _ticket_values(ticket):
    if ticket is None:
        return {
            "user_id": "",
            "address": "",
            "apartment": "",
            "contact_phone": "",
            "problem": "",
            "work_type_id": "",
            "payment_type_id": "",
            "status_id": "",
            "visit_date": "",
        }
    return {
        "user_id": ticket.user_id,
        "address": ticket.address,
        "apartment": ticket.apartment,
        "contact_phone": ticket.contact_phone,
        "problem": ticket.problem,
        "work_type_id": ticket.work_type_id,
        "payment_type_id": ticket.payment_type_id,
        "status_id": ticket.status_id,
        "visit_date": ticket.visit_date.isoformat() if ticket.visit_date else "",
    }


def _subscribers(ticket):
    rows = db.session.execute(
        select(User).where(User.role == "user").order_by(User.full_name)
    ).scalars().all()
    if ticket and ticket.user and ticket.user not in rows:
        rows = [ticket.user, *rows]
    return rows


def _ticket_filters(args):
    clauses = []
    status = (args.get("status") or "").strip()
    work_type = (args.get("work_type") or "").strip()
    query = (args.get("q") or "").strip()
    if status:
        clauses.append(Status.code == status)
    if work_type.isdigit():
        clauses.append(Request.work_type_id == int(work_type))
    if query:
        pattern = _like(query)
        clauses.append(or_(
            Request.address.like(pattern, escape="\\"),
            Request.problem.like(pattern, escape="\\"),
            User.full_name.like(pattern, escape="\\"),
            Request.contact_phone.like(pattern, escape="\\"),
            User.login.like(pattern, escape="\\"),
        ))
    return clauses, {"status": status, "work_type": work_type, "q": query}


def _like(text):
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _tickets_url():
    return url_for(
        "admin.tickets",
        q=request.form.get("q", ""),
        status=request.form.get("status", ""),
        work_type=request.form.get("work_type", ""),
        page=request.form.get("page", 1),
    )
