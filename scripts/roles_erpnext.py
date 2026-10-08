#!/usr/bin/env python3
"""
Crea/actualiza los dos roles de integración de Voraz en ERPNext
(«Voraz Lectura» y «Voraz Integracion») sobre los doctypes que usa la integración.

═══════════════════════════════════════════════════════════════════════════════
⚠️  LEER ANTES DE EJECUTAR — la trampa que costó una caída de permisos
═══════════════════════════════════════════════════════════════════════════════
En Frappe, si un DocType tiene ALGUNA fila en `tabCustom DocPerm`, esa tabla
pasa a ser la ÚNICA fuente de permisos para ese DocType y `tabDocPerm` (la
estándar) se IGNORA por completo — para TODOS los roles, no solo para los
nuevos. Ver frappe/permissions.py:

    doctypes_with_custom_perms = get_doctypes_with_custom_docperms()
    for p in perms:
        if p.parent not in doctypes_with_custom_perms:   # la estándar solo
            custom_perms.append(p)                       # cuenta sin custom

Consecuencia: agregar un rol nuevo «a mano» en un DocType deja sin permisos a
todos los demás usuarios de ese DocType (Administrator no se ve afectado, porque
tiene bypass). Pasó el 2026-10-08: Juanma perdió el acceso a ventas.

Por eso este script SIEMPRE copia la matriz estándar completa a la custom
(con frappe.permissions.copy_perms) antes de agregar los roles propios. Es el
mismo resultado que produce la UI de Frappe al «personalizar» permisos.

═══════════════════════════════════════════════════════════════════════════════
Uso (dentro del contenedor del ERP, ver docs/runbook.md §7):

    docker cp scripts/roles_erpnext.py frappe-backend-1:/tmp/
    docker exec -u root frappe-backend-1 chmod 644 /tmp/roles_erpnext.py
    docker exec frappe-backend-1 bash -lc \
      'cd /home/frappe/frappe-bench/sites && ../env/bin/python /tmp/roles_erpnext.py'

Es idempotente: se puede correr las veces que haga falta.
Antes de correrlo, sacar respaldo de `tabCustom DocPerm`.
"""
import frappe
from frappe.permissions import copy_perms

SITE = "vorazadmin.site"

# Roles propios: nombre -> flags de permiso
ROLES = {
    "Voraz Lectura":     ["read", "report", "export", "print", "email"],
    "Voraz Integracion": ["read", "write", "create", "submit", "cancel", "delete",
                          "amend", "report", "export", "print", "email", "share"],
}

# DocTypes que la integración toca (lectura o escritura)
DOCTYPES = [
    # ventas
    "Sales Order", "Sales Invoice", "Delivery Note", "Customer", "Customer Group",
    "Sales Person", "Territory", "Item", "Item Group", "Item Price", "UOM",
    # inventario
    "Bin", "Stock Entry", "Warehouse",
    # contabilidad
    "Account", "Cost Center", "Currency", "GL Entry", "Journal Entry",
    "Mode of Payment", "Payment Entry", "Company",
]

# Usuarios de prueba para la verificación final: etiqueta -> email
VERIFICAR = {
    "integracion@": "vorazcde@gmail.com",
    "consulta@":    "xjuanmax@hotmail.com",
}
# Un usuario con roles estándar (Sales Manager) para confirmar que NO se rompió
USUARIO_ESTANDAR = "xjuanma.romerox@gmail.com"


def flags(fila, cols=("read", "write", "create", "submit", "cancel", "delete",
                      "amend", "report", "export", "print", "email", "share")):
    return [c for c in cols if fila.get(c)]


def main():
    frappe.init(site=SITE)
    frappe.connect()
    frappe.set_user("Administrator")

    # 0) Respaldo del estado actual
    import json
    respaldo = frappe.db.sql("select * from `tabCustom DocPerm`", as_dict=True)
    with open("/tmp/voraz_custom_docperm_backup.json", "w") as f:
        json.dump(respaldo, f, default=str, indent=1)
    print("VPZ_BACKUP|%d filas -> /tmp/voraz_custom_docperm_backup.json" % len(respaldo))

    # 1) Los roles tienen que existir
    for rol in ROLES:
        if not frappe.db.exists("Role", rol):
            frappe.get_doc({"doctype": "Role", "role_name": rol, "desk_access": 1}).insert(
                ignore_permissions=True)
            print("VPZ_ROL_CREADO|%s" % rol)
    frappe.db.commit()

    # 2) Por cada DocType: copiar la estándar (clave) y agregar los roles propios
    for dt in DOCTYPES:
        tenia_custom = frappe.db.exists("Custom DocPerm", {"parent": dt})
        if not tenia_custom:
            copy_perms(dt)
            print("VPZ_COPIA_ESTANDAR|%s|(no tenia custom)" % dt)
        else:
            # Ya hay custom: copiar solo las reglas estándar que falten
            agregadas = 0
            for d in frappe.get_all("DocPerm", fields="*", filters=dict(parent=dt)):
                if frappe.db.exists("Custom DocPerm", {
                        "parent": dt, "role": d.role, "permlevel": d.permlevel,
                        "if_owner": d.if_owner}):
                    continue
                cp = frappe.new_doc("Custom DocPerm")
                cp.update(d)
                cp.insert(ignore_permissions=True)
                agregadas += 1
            if agregadas:
                print("VPZ_COPIA_ESTANDAR|%s|%d reglas que faltaban" % (dt, agregadas))

        for rol, permisos in ROLES.items():
            existe = frappe.db.exists("Custom DocPerm", {"parent": dt, "role": rol, "permlevel": 0})
            doc = frappe.get_doc("Custom DocPerm", existe) if existe else frappe.new_doc("Custom DocPerm")
            doc.parent = dt
            doc.role = rol
            doc.permlevel = 0
            for p in ["read", "write", "create", "submit", "cancel", "delete",
                      "amend", "report", "export", "print", "email", "share"]:
                doc.set(p, 1 if p in permisos else 0)
            doc.if_owner = 0
            if existe:
                doc.save(ignore_permissions=True)
            else:
                doc.insert(ignore_permissions=True)
            print("VPZ_ROL_OK|%s|%s|%s" % (dt, rol, ",".join(permisos)))
        frappe.db.commit()

    frappe.clear_cache()

    # 3) Verificación
    print()
    print("=== VERIFICACION ===")
    for dt in ["Sales Order", "Sales Invoice", "Delivery Note", "Customer", "Item", "GL Entry"]:
        estado = []
        for etiqueta, u in VERIFICAR.items():
            estado.append("%s=leer:%s/escribir:%s" % (
                etiqueta,
                frappe.has_permission(dt, ptype="read", user=u),
                frappe.has_permission(dt, ptype="write", user=u)))
        estado.append("usuario_estandar=leer:%s" % frappe.has_permission(
            dt, ptype="read", user=USUARIO_ESTANDAR))
        print("VPZ_VERIF|%s|%s" % (dt, "|".join(estado)))

    print("VPZ_DONE")


if __name__ == "__main__":
    main()
