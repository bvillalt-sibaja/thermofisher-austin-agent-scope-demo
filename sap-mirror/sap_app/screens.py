"""All SAP-mirror screen builders.

Each build_* function clears `parent` and lays out a screen into it. Screens
are driven by a `session` object (see app.SAPSession) exposing:
  session.data            - shared DemoData
  session.show(name, **ctx) - navigate to another screen, ctx stored on session.ctx
  session.back()          - pop nav history
  session.set_status(text)
  session.win             - the Tk/Toplevel window (for popups)

Interactive widgets are given a Tkinter `name=` for RPA targeting instead of
relying on pixel coordinates - see BUILD_NOTES.md for the naming convention.
"""

import tkinter as tk
from tkinter import ttk

from sap_app import theme, icons
from sap_app.popups import confirm_dialog, info_popup


def _clear(parent):
    for w in parent.winfo_children():
        w.destroy()


def _header(parent, text, name):
    hdr = tk.Frame(parent, bg=theme.HEADER_BG, name=name)
    hdr.pack(side="top", fill="x")
    tk.Label(hdr, text=text, bg=theme.HEADER_BG, fg=theme.HEADER_FG,
              font=theme.FONT_HEADER, anchor="w").pack(side="left", padx=10, pady=7)
    rule = tk.Frame(parent, bg=theme.GROUPBOX_BORDER, height=1)
    rule.pack(side="top", fill="x")
    return hdr


def _field_row(parent, label, name, width=20, value="", required=True):
    row = tk.Frame(parent, bg=theme.CONTENT_BG)
    row.pack(anchor="w", padx=14, pady=4, fill="x")
    tk.Label(row, text=label, bg=theme.CONTENT_BG, font=theme.FONT_NORMAL,
              width=22, anchor="w").pack(side="left")
    var = tk.StringVar(value=value)
    entry = tk.Entry(row, textvariable=var, font=theme.FONT_NORMAL, width=width, name=name,
                       relief="sunken", bd=2, bg=theme.REQUIRED_BG if required else theme.CONTENT_BG)
    entry.pack(side="left")
    return var, entry


def _readonly_row(parent, label, value, name, linkable=False, command=None):
    row = tk.Frame(parent, bg=theme.CONTENT_BG)
    row.pack(anchor="w", padx=14, pady=3, fill="x")
    tk.Label(row, text=label, bg=theme.CONTENT_BG, font=theme.FONT_NORMAL,
              width=22, anchor="w").pack(side="left")
    fg = theme.LINK_FG if linkable else "black"
    lbl = tk.Label(row, text=value, bg="#EAF2FF" if linkable else "#F5F5F0",
                    fg=fg, font=theme.FONT_NORMAL, name=name, relief="sunken", bd=1,
                    padx=4, width=20, anchor="w")
    lbl.pack(side="left")
    if linkable and command:
        lbl.bind("<Double-Button-1>", lambda e: command())
    return lbl


def _back_bar(parent, session, extra_buttons=None):
    bar = tk.Frame(parent, bg=theme.TOOLBAR_BG, name="nav_bar",
                     highlightbackground=theme.GROUPBOX_BORDER, highlightthickness=1)
    bar.pack(side="bottom", fill="x")
    tk.Button(bar, text=" Back", name="btn_back", width=10, image=icons.get("back"),
               compound="left", font=theme.FONT_SMALL, command=session.back).pack(
        side="left", padx=6, pady=4)
    for label, name, cmd in (extra_buttons or []):
        tk.Button(bar, text=label, name=name, font=theme.FONT_SMALL, command=cmd).pack(
            side="left", padx=6, pady=4)
    return bar


# --------------------------------------------------------------------- LOGIN

def build_login_select(session, parent):
    _clear(parent)
    _header(parent, "SAP Logon 750 - Select System", "hdr_login_select")
    tk.Label(parent, text="Select a system to log on to:", bg=theme.CONTENT_BG,
              font=theme.FONT_NORMAL).pack(anchor="w", padx=14, pady=(14, 6))

    listbox = tk.Listbox(parent, font=theme.FONT_NORMAL, height=8, width=50, name="system_list",
                           relief="sunken", bd=2, selectbackground=theme.TITLE_BG,
                           selectforeground="#FFFFFF", highlightthickness=0)
    systems = ["070. LSG Prodcution", "071. LSG Quality (QAS)", "072. LSG Development (DEV)"]
    for s in systems:
        listbox.insert("end", s)
    listbox.pack(anchor="w", padx=14, pady=4)

    def choose(event=None):
        sel = listbox.curselection()
        if not sel:
            return
        session.show("LOGIN_SYSTEM_LIST")

    listbox.bind("<Double-Button-1>", choose)
    tk.Button(parent, text="Log On", name="btn_logon_select", command=choose).pack(anchor="w", padx=14, pady=8)


def build_login_system_list(session, parent):
    _clear(parent)
    _header(parent, "LSG Production Systems", "hdr_lsg_list")
    tk.Label(parent, text="Select a server:", bg=theme.CONTENT_BG,
              font=theme.FONT_NORMAL).pack(anchor="w", padx=14, pady=(14, 6))
    listbox = tk.Listbox(parent, font=theme.FONT_NORMAL, height=5, width=50, name="lsg_system_list",
                           relief="sunken", bd=2, selectbackground=theme.TITLE_BG,
                           selectforeground="#FFFFFF", highlightthickness=0)
    for s in ["PS1 - LSG Production (Austin)", "PS2 - LSG Production (Mirror)"]:
        listbox.insert("end", s)
    listbox.selection_set(0)
    listbox.pack(anchor="w", padx=14, pady=4)

    def choose(event=None):
        session.show("LOGIN_CREDS")

    listbox.bind("<Double-Button-1>", choose)
    tk.Button(parent, text="Enter", name="btn_lsg_enter", command=choose).pack(anchor="w", padx=14, pady=8)


def build_login_creds(session, parent):
    _clear(parent)
    _header(parent, "SAP - PS1 - LSG Production (Austin)", "hdr_login")
    box = tk.Frame(parent, bg=theme.CONTENT_BG)
    box.pack(pady=30)
    user_var, user_entry = _field_row(box, "User Name", "field_username")
    pwd_var = tk.StringVar()
    row = tk.Frame(box, bg=theme.CONTENT_BG)
    row.pack(anchor="w", padx=14, pady=4, fill="x")
    tk.Label(row, text="Password", bg=theme.CONTENT_BG, font=theme.FONT_NORMAL,
              width=22, anchor="w").pack(side="left")
    tk.Entry(row, textvariable=pwd_var, font=theme.FONT_NORMAL, width=20, show="*",
              name="field_password").pack(side="left")

    def do_login(event=None):
        session.set_status(f"Logged on as {user_var.get() or 'DEMO_USER'}")
        session.show("EASY_ACCESS")

    session.win.bind("<Return>", do_login)
    tk.Button(box, text="Enter", name="btn_login_enter", command=do_login).pack(anchor="w", padx=14, pady=10)


# --------------------------------------------------------------- EASY ACCESS

def build_easy_access(session, parent):
    _clear(parent)
    _header(parent, "SAP Easy Access", "hdr_easy_access")
    tk.Label(parent, text="Favorites", bg=theme.CONTENT_BG, font=theme.FONT_BOLD,
              anchor="w").pack(anchor="w", padx=10, pady=(10, 2))

    items = [
        ("Display Stock / Requirements", "nav_stock_req", lambda: session.show("STOCK_REQ", mode="general")),
        ("Display Stock / Requirements Situation", "nav_stock_req_2", lambda: session.show("STOCK_REQ", mode="general")),
        ("Material Doc List", "nav_matdoc", lambda: session.show("MATDOC_LIST")),
        ("Change Production Order (CO02)", "nav_co02", lambda: session.show("PO_CHANGE")),
    ]
    for label, name, cmd in items:
        row = tk.Frame(parent, bg=theme.CONTENT_BG)
        row.pack(anchor="w", padx=24, pady=2, fill="x")
        tk.Label(row, text="■", bg=theme.CONTENT_BG, fg="#F0C040",
                  font=theme.FONT_NORMAL).pack(side="left", padx=(0, 6))
        lbl = tk.Label(row, text=label, bg=theme.CONTENT_BG, fg=theme.LINK_FG,
                         font=theme.FONT_NORMAL, name=name, anchor="w", cursor="hand2")
        lbl.pack(side="left")
        lbl.bind("<Double-Button-1>", lambda e, c=cmd: c())
        row.bind("<Double-Button-1>", lambda e, c=cmd: c())


# ---------------------------------------------------------- STOCK/REQUIREMENTS

def build_stock_req(session, parent):
    _clear(parent)
    mode = session.ctx.get("mode", "general")
    title = "Stock/Requirements List - Individual Access" if mode == "individual" else "Stock/Requirements List"
    _header(parent, title, "hdr_stock_req")

    mat_var, mat_entry = _field_row(parent, "Material", "field_material", value=session.current_material or "")
    mat_entry.focus_set()

    result_frame = tk.Frame(parent, bg=theme.CONTENT_BG, name="stock_req_results")
    result_frame.pack(fill="both", expand=True, padx=10, pady=6)

    def render_results():
        _clear(result_frame)
        mat_no = mat_var.get().strip()
        mat = session.data.get_material(mat_no)
        if not mat:
            tk.Label(result_frame, text=f"Material {mat_no} does not exist.", bg=theme.CONTENT_BG,
                      fg="red", font=theme.FONT_NORMAL).pack(anchor="w", pady=10)
            return
        session.current_material = mat_no
        tk.Label(result_frame, text=f"{mat_no} - {mat['description']}", bg=theme.CONTENT_BG,
                  font=theme.FONT_BOLD).pack(anchor="w", pady=(4, 8))

        _readonly_row(result_frame, "Available qty", f"{mat['available_qty']} {mat['uom']}",
                       "val_available_qty", linkable=True,
                       command=lambda: session.show("STOCK_OVERVIEW", material=mat_no))

        order_no = mat.get("production_order")
        order_text = order_no if order_no else "(none)"
        _readonly_row(result_frame, "Production Order", order_text, "val_production_order",
                       linkable=bool(order_no),
                       command=(lambda: session.show("PO_CHANGE", order=order_no)) if order_no else None)

        _readonly_row(result_frame, "MRP element data", mat["mrp_element"], "val_mrp_element",
                       linkable=True, command=lambda: on_mrp_double_click(mat_no))

        tk.Button(result_frame, text="Change", name="btn_change",
                   command=lambda: session.show("STOCK_REQ_CHANGE", material=mat_no)).pack(anchor="w", pady=10)

    def on_mrp_double_click(mat_no):
        edit = confirm_dialog(session.win, "Additional Data for MRP Element",
                                "Edit MRP element additional data?", name="mrp_edit_confirm")
        if edit:
            mat = session.data.get_material(mat_no)
            order_no = mat.get("production_order") if mat else None
            if order_no:
                session.show("PO_CHANGE", order=order_no)
            else:
                session.show("PO_CREATE", material=mat_no)

    def on_enter(event=None):
        render_results()

    mat_entry.bind("<Return>", on_enter)
    tk.Button(parent, text="Enter", name="btn_stock_req_enter", command=on_enter).pack(anchor="w", padx=14)

    if session.current_material:
        mat_var.set(session.current_material)
        render_results()

    _back_bar(parent, session)


def build_stock_req_change(session, parent):
    _clear(parent)
    mat_no = session.ctx.get("material", session.current_material)
    mat = session.data.get_material(mat_no) or {}
    _header(parent, f"Change Material {mat_no}", "hdr_stock_req_change")

    tabs = ttk.Notebook(parent, name="change_tabs")
    tabs.pack(fill="both", expand=True, padx=10, pady=8)

    basic = tk.Frame(tabs, bg=theme.CONTENT_BG)
    tabs.add(basic, text="Basic Data")
    _readonly_row(basic, "Material", mat_no, "val_change_material")
    _readonly_row(basic, "Description", mat.get("description", ""), "val_change_description")

    plant = tk.Frame(tabs, bg=theme.CONTENT_BG)
    tabs.add(plant, text="Plant data / stor.")
    pd = mat.get("plant_data", {})
    _readonly_row(plant, "Plant", pd.get("plant", ""), "val_plant")
    _readonly_row(plant, "MRP Group", pd.get("mrp_group", ""), "val_mrp_group")
    _readonly_row(plant, "MRP Type", pd.get("mrp_type", ""), "val_mrp_type")

    addl = tk.Frame(tabs, bg=theme.CONTENT_BG)
    tabs.add(addl, text="Additional Data")
    doc_lbl = _readonly_row(addl, "Document Data", "Document: SPEC-" + mat_no, "val_document_link",
                              linkable=True, command=lambda: session.show("DOCUMENT_VIEW", material=mat_no))

    _back_bar(parent, session)


def build_stock_overview(session, parent):
    _clear(parent)
    mat_no = session.ctx.get("material", session.current_material)
    mat = session.data.get_material(mat_no) or {}
    _header(parent, "Stock Overview: Basic List", "hdr_stock_overview")

    tk.Label(parent, text=f"Material: {mat_no}   Plant: {mat.get('plant_data', {}).get('plant', '')}",
              bg=theme.CONTENT_BG, font=theme.FONT_NORMAL).pack(anchor="w", padx=14, pady=(10, 8))

    _readonly_row(parent, "Stor. loc.", mat.get("stor_loc", ""), "val_stor_loc", linkable=True,
                   command=lambda: info_popup(session.win, "Storage Location",
                                                mat.get("stor_loc", ""), name="stor_loc_popup"))
    _readonly_row(parent, "Batch", mat.get("batch", ""), "val_batch", linkable=True,
                   command=lambda: session.show("BATCH_CLASSIFICATION", material=mat_no))

    _back_bar(parent, session, extra_buttons=[
        ("Refresh", "btn_refresh", lambda: session.set_status("Refreshed.", ok=True)),
        ("Close", "btn_close", session.back),
    ])


def build_batch_classification(session, parent):
    _clear(parent)
    mat_no = session.ctx.get("material", session.current_material)
    mat = session.data.get_material(mat_no) or {}
    _header(parent, "Batch Classification", "hdr_batch_classification")
    _readonly_row(parent, "Batch", mat.get("batch", ""), "val_batch_classification")
    _readonly_row(parent, "Status", "Unrestricted-Use", "val_batch_status")
    _readonly_row(parent, "Shelf Life Exp. Date", "2027-01-15", "val_batch_sled")
    _back_bar(parent, session)


def build_document_view(session, parent):
    _clear(parent)
    mat_no = session.ctx.get("material", session.current_material)
    _header(parent, "Document Data", "hdr_document_view")
    tk.Label(parent, text=f"Document: SPEC-{mat_no}\nType: Specification Sheet\nApplication: WORD",
              bg=theme.CONTENT_BG, font=theme.FONT_NORMAL, justify="left").pack(anchor="w", padx=14, pady=14)
    tk.Button(parent, text="Open Application (Word)", name="btn_open_document",
               command=lambda: session.set_status("Opening document in Word (demo)...", ok=True)
               ).pack(anchor="w", padx=14)
    _back_bar(parent, session)


# ---------------------------------------------------------- PRODUCTION ORDER

def _po_component_tab(session, parent, order):
    frame = tk.Frame(parent, bg=theme.CONTENT_BG)
    mat_var, _ = _field_row(frame, "Material", "field_po_material",
                              value=order.get("material", "") if order else session.current_material or "")
    cat_var, _ = _field_row(frame, "Item Category", "field_po_item_category",
                              value=order.get("item_category", "") if order else "")
    batch_var, _ = _field_row(frame, "Batch", "field_po_batch", value=(order or {}).get("batch") or "")
    qty_var, _ = _field_row(frame, "Total quant.", "field_po_total_quant",
                              value=order.get("total_quant", "") if order else "")

    def select_item():
        ok = confirm_dialog(session.win, "Confirmation", "Confirm this component item?", name="po_item_confirm")
        if ok:
            session.set_status("Item confirmed.", ok=True)

    tk.Button(frame, text="Select Item", name="btn_po_select_item", command=select_item).pack(anchor="w", padx=14, pady=6)
    return frame, mat_var, cat_var, batch_var, qty_var


def _po_allocation_tab(parent, order):
    frame = tk.Frame(parent, bg=theme.CONTENT_BG)
    oper_var, _ = _field_row(frame, "Oper.", "field_po_oper", value="0010")
    tk.Button(frame, text="Check", name="btn_po_check",
               command=lambda: None).pack(anchor="w", padx=14, pady=6)
    return frame, oper_var


def _po_long_text_tab(session, parent, order, key):
    frame = tk.Frame(parent, bg=theme.CONTENT_BG)
    text = tk.Text(frame, font=theme.FONT_NORMAL, width=60, height=6, name="field_po_long_text")
    text.pack(padx=14, pady=10)
    if order:
        text.insert("1.0", order.get(key, ""))

    def on_enter(event=None):
        if order is not None:
            order[key] = text.get("1.0", "end").strip()
        session.set_status("Long text saved.", ok=True)
        return "break"

    text.bind("<Return>", on_enter)
    return frame, text


def _po_goods_receipt_tab(session, parent, order):
    frame = tk.Frame(parent, bg=theme.CONTENT_BG)

    def create_batch():
        allocate = confirm_dialog(session.win, "Automatic Batch Number Allocation",
                                    "Create batch automatically?", name="auto_batch_confirm")
        if allocate and order is not None:
            order["batch"] = "AUTO-" + order["order_no"]
            session.set_status(f"Batch {order['batch']} created.", ok=True)

    tk.Button(frame, text="Goods recept.", name="btn_goods_receipt",
               command=lambda: session.set_status("Goods receipt posted (demo).", ok=True)).pack(anchor="w", padx=14, pady=6)
    tk.Button(frame, text="Create Automatic Batch", name="btn_create_auto_batch",
               command=create_batch).pack(anchor="w", padx=14, pady=6)
    return frame


def _po_general_tab(session, parent, order, show_release=True, show_print=False):
    frame = tk.Frame(parent, bg=theme.CONTENT_BG)
    start_var, _ = _field_row(frame, "Start Date", "field_po_start_date",
                                value=order.get("start_date", "") if order else "")
    finish_var, _ = _field_row(frame, "Finish Date", "field_po_finish_date",
                                 value=order.get("finish_date", "") if order else "")

    btn_row = tk.Frame(frame, bg=theme.CONTENT_BG)
    btn_row.pack(anchor="w", padx=14, pady=10)
    if show_release:
        tk.Button(btn_row, text="Release", name="btn_po_release",
                   command=lambda: (order.update(released=True) if order else None,
                                     session.set_status("Order released.", ok=True))
                   ).pack(side="left", padx=4)
    tk.Button(btn_row, text="Save", name="btn_po_save",
               command=lambda: (order.update(saved=True) if order else None,
                                 session.set_status(f"Order {order['order_no']} saved." if order else "Saved.", ok=True))
               ).pack(side="left", padx=4)
    if show_print:
        tk.Button(btn_row, text="Print", name="btn_po_print",
                   command=lambda: session.show("PO_PRINT_PREVIEW", order=order["order_no"] if order else None)
                   ).pack(side="left", padx=4)
    return frame, start_var, finish_var


def build_po_create(session, parent):
    _clear(parent)
    mat_no = session.ctx.get("material", session.current_material)
    _header(parent, "Create Production Order", "hdr_po_create")

    tabs = ttk.Notebook(parent, name="po_create_tabs")
    tabs.pack(fill="both", expand=True, padx=10, pady=8)

    state = {"order": None}

    comp_frame, mat_var, cat_var, batch_var, qty_var = _po_component_tab(session, tabs, None)
    tabs.add(comp_frame, text="Component Overview")

    alloc_frame, oper_var = _po_allocation_tab(tabs, None)
    tabs.add(alloc_frame, text="Allocation Operations/Sequence")

    lt_frame, lt_text = _po_long_text_tab(session, tabs, None, "long_text_create")
    tabs.add(lt_frame, text="Long Text")

    gr_frame = _po_goods_receipt_tab(session, tabs, None)
    tabs.add(gr_frame, text="Goods recept.")

    gen_frame, start_var, finish_var = _po_general_tab(session, tabs, None, show_release=True)
    tabs.add(gen_frame, text="General")

    def do_save():
        order = session.data.create_production_order(
            mat_var.get().strip(), cat_var.get().strip(), qty_var.get().strip(),
            lt_text.get("1.0", "end").strip(), start_var.get().strip(), finish_var.get().strip())
        session.set_status(f"Order {order['order_no']} created and saved.", ok=True)
        session.current_material = mat_var.get().strip()

    # Rebind Save on the General tab to actually create the order (component data lives on other tabs).
    for child in gen_frame.winfo_children():
        pass
    save_btn = gen_frame.nametowidget("btn_po_save") if "btn_po_save" in [c.winfo_name() for c in gen_frame.winfo_children()] else None
    # simpler: find by name search
    def find_named(widget, name):
        if widget.winfo_name() == name:
            return widget
        for c in widget.winfo_children():
            r = find_named(c, name)
            if r:
                return r
        return None
    btn = find_named(gen_frame, "btn_po_save")
    if btn:
        btn.configure(command=do_save)

    _back_bar(parent, session)


def build_po_change(session, parent):
    _clear(parent)
    _header(parent, "Change Production Order", "hdr_po_change")

    order_no = session.ctx.get("order")
    order = session.data.get_order(order_no) if order_no else None

    order_var, order_entry = _field_row(parent, "Order", "field_po_order", value=order_no or "")

    body = tk.Frame(parent, bg=theme.CONTENT_BG, name="po_change_body")
    body.pack(fill="both", expand=True)

    def render(order_obj):
        _clear(body)
        if not order_obj:
            tk.Label(body, text="Enter an order number and press Enter.", bg=theme.CONTENT_BG,
                      font=theme.FONT_NORMAL).pack(anchor="w", padx=14, pady=10)
            return
        tabs = ttk.Notebook(body, name="po_change_tabs")
        tabs.pack(fill="both", expand=True, padx=10, pady=8)

        comp_frame, mat_var, cat_var, batch_var, qty_var = _po_component_tab(session, tabs, order_obj)
        tabs.add(comp_frame, text="Component Overview")

        lt_frame, lt_text = _po_long_text_tab(session, tabs, order_obj, "long_text_change")
        tabs.add(lt_frame, text="Long Text")

        gen_frame, start_var, finish_var = _po_general_tab(session, tabs, order_obj, show_release=False, show_print=True)
        tabs.add(gen_frame, text="General")

    def on_enter(event=None):
        o = session.data.get_order(order_var.get().strip())
        if not o:
            session.set_status(f"Order {order_var.get().strip()} does not exist.", ok=False)
        render(o)

    order_entry.bind("<Return>", on_enter)
    tk.Button(parent, text="Enter", name="btn_po_change_enter", command=on_enter).pack(anchor="w", padx=14)

    if order:
        render(order)

    _back_bar(parent, session)


def build_po_print_preview(session, parent):
    _clear(parent)
    order_no = session.ctx.get("order")
    order = session.data.get_order(order_no) if order_no else None
    _header(parent, "Print Preview", "hdr_po_print")
    text = f"PRODUCTION ORDER {order_no}\n\n" + (
        f"Material: {order['material']}\nQty: {order['total_quant']}\nStatus: {order['status']}"
        if order else "(no order)")
    tk.Label(parent, text=text, bg=theme.CONTENT_BG, font=theme.FONT_NORMAL, justify="left").pack(
        anchor="w", padx=14, pady=14)
    _back_bar(parent, session)


# ------------------------------------------------------------- MATERIAL DOCS

def build_matdoc_list(session, parent):
    _clear(parent)
    _header(parent, "Material Document List", "hdr_matdoc_list")
    mat_var, mat_entry = _field_row(parent, "Material", "field_matdoc_material",
                                      value=session.current_material or "")

    results = tk.Frame(parent, bg=theme.CONTENT_BG, name="matdoc_results")
    results.pack(fill="both", expand=True, padx=10, pady=6)

    def execute(event=None):
        _clear(results)
        mat_no = mat_var.get().strip()
        orders = session.data.find_orders_by_material(mat_no)
        if not orders:
            tk.Label(results, text=f"No material documents found for {mat_no}.", bg=theme.CONTENT_BG,
                      font=theme.FONT_NORMAL).pack(anchor="w", pady=10)
            return
        tk.Label(results, text="Order", bg=theme.GRID_HEADER_BG, font=theme.FONT_BOLD,
                  anchor="w", padx=4).pack(anchor="w", fill="x")
        for i, o in enumerate(orders):
            row_bg = theme.GRID_ROW_ALT_BG if i % 2 else theme.CONTENT_BG
            lbl = tk.Label(results, text=o["order_no"], bg=row_bg, fg=theme.LINK_FG,
                             font=theme.FONT_NORMAL, name=f"row_order_{o['order_no']}", anchor="w",
                             relief="flat", padx=4)
            lbl.pack(anchor="w", pady=0, fill="x")
            lbl.bind("<Double-Button-1>", lambda e, on=o["order_no"]: session.show("PO_DISPLAY", order=on))

    mat_entry.bind("<Return>", execute)
    tk.Button(parent, text="Execute", name="btn_matdoc_execute", command=execute).pack(anchor="w", padx=14, pady=4)

    if session.current_material:
        execute()

    _back_bar(parent, session)


def build_po_display(session, parent):
    _clear(parent)
    order_no = session.ctx.get("order")
    order = session.data.get_order(order_no) if order_no else None
    _header(parent, f"Display Material Document - Order {order_no}", "hdr_po_display")

    if not order:
        tk.Label(parent, text="Order not found.", bg=theme.CONTENT_BG, font=theme.FONT_NORMAL).pack(
            anchor="w", padx=14, pady=10)
        _back_bar(parent, session)
        return

    _readonly_row(parent, "Order", order["order_no"], "val_display_order")
    _readonly_row(parent, "Material", order["material"], "val_display_material")
    _readonly_row(parent, "Component Overview", "1 component", "val_component_overview",
                   linkable=True, command=lambda: info_popup(
                       session.win, "Component Overview",
                       f"Material: {order['material']}\nQty: {order['total_quant']}",
                       name="component_overview_popup"))

    _back_bar(parent, session)
