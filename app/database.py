import sqlite3
from datetime import datetime

DB_NAME = "pedidos.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            order_id TEXT PRIMARY KEY,
            cliente TEXT,
            titulo TEXT,
            cantidad INTEGER,
            estado TEXT DEFAULT 'pendiente',
            fecha_armado TEXT,
            fecha_despacho TEXT,
            logistica TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_order_if_not_exists(order_id, detalle):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # tabla ya creada por init_db()
    cursor.execute("SELECT 1 FROM pedidos WHERE order_id = ?", (order_id,))
    if cursor.fetchone() is None:
        cursor.execute(
            """
            INSERT INTO pedidos (order_id, cliente, titulo, cantidad, estado)
            VALUES (?, ?, ?, ?, 'pendiente')
            """,
            (
                order_id,
                detalle.get("cliente"),
                detalle.get("titulo"),
                detalle.get("cantidad"),
            )
        )
    conn.commit()
    conn.close()


def marcar_pedido_armado(order_id):
    """
    Actualiza el estado a 'armado' y registra la fecha de armado.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE pedidos
        SET estado = 'armado', fecha_armado = ?
        WHERE order_id = ?
        """,
        (datetime.now().isoformat(), order_id)
    )
    updated = cursor.rowcount
    conn.commit()
    conn.close()
    return updated > 0


def marcar_pedido_despachado(order_id, logistica):
    """
    Actualiza el estado a 'despachado', registra fecha y logística.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Verificar si existe el pedido
    cursor.execute("SELECT estado FROM pedidos WHERE order_id = ?", (order_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    current = row[0]
    # Sólo despachar si está armado
    if current != 'armado':
        conn.close()
        return False

    cursor.execute(
        """
        UPDATE pedidos
        SET estado = 'despachado', fecha_despacho = ?, logistica = ?
        WHERE order_id = ?
        """,
        (datetime.now().isoformat(), logistica, order_id)
    )
    updated = cursor.rowcount
    conn.commit()
    conn.close()
    return updated > 0


def despachar_pedido(order_id, logistica):
    """
    Lógica de despachar que devuelve diccionario con mensajes para la API.
    """
    ok = marcar_pedido_despachado(order_id, logistica)
    if ok:
        return {"success": True, "mensaje": "Pedido despachado correctamente"}
    else:
        return {"success": False, "error": "No se pudo despachar el pedido. Asegúrate que esté armado."}


def get_pedidos_por_estado(estado):
    """
    Devuelve lista de pedidos con el estado dado.
    Cada pedido es un dict con campos: order_id, cliente, titulo, cantidad,
    estado, fecha_armado, fecha_despacho, logistica.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT order_id, cliente, titulo, cantidad, estado, fecha_armado, fecha_despacho, logistica"
        " FROM pedidos WHERE estado = ?",
        (estado,)
    )
    rows = cursor.fetchall()
    conn.close()

    pedidos = []
    for row in rows:
        pedidos.append({
            'order_id':       row[0],
            'cliente':        row[1],
            'titulo':         row[2],
            'cantidad':       row[3],
            'estado':         row[4],
            'fecha_armado':   row[5],
            'fecha_despacho': row[6],
            'logistica':      row[7]
        })
    return pedidos


def get_pedidos_pendientes():
    """Pedidos aún sin armar ni despachar"""
    return get_pedidos_por_estado('pendiente')


def get_pedidos_armados():
    """Pedidos marcados como armados y a la espera de despacho"""
    return get_pedidos_por_estado('armado')


def get_pedidos_despachados():
    """Pedidos ya despachados"""
    return get_pedidos_por_estado('despachado')

def get_all_pedidos(order_id: str = None,
                    date_from: str = None,
                    date_to:   str = None,
                    logistica: str = None) -> list[dict]:
    conn   = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    query  = """
        SELECT order_id, cliente, titulo, cantidad,
               estado, fecha_armado, fecha_despacho, logistica
        FROM pedidos
        WHERE 1=1
    """
    params = []

    if order_id:
        query += " AND order_id LIKE ?"
        params.append(f"%{order_id}%")
    if date_from:
        query += " AND (fecha_armado >= ? OR fecha_despacho >= ?)"
        params.extend([date_from, date_from])
    if date_to:
        query += " AND (fecha_armado <= ? OR fecha_despacho <= ?)"
        params.extend([date_to, date_to])
    if logistica:
        query += " AND logistica = ?"
        params.append(logistica)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    pedidos = []
    for row in rows:
        pedidos.append({
            "order_id":      row[0],
            "cliente":       row[1],
            "titulo":        row[2],
            "cantidad":      row[3],
            "estado":        row[4],
            "fecha_armado":  row[5],
            "fecha_despacho":row[6],
            "logistica":     row[7]
        })
    return pedidos