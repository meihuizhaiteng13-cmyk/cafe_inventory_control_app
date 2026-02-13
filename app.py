from flask import Flask, render_template, request, redirect, url_for, flash, abort
import sqlite3
from pathlib import Path

app = Flask(__name__)
app.secret_key = "dev-secret-key"

# 店主用 仮パスコード（必要なら変更OK）
OWNER_PASSCODE = "1234"

# DBパス（このフォルダ内の inventory.db）
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "inventory.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------
# 在庫一覧
# -------------------------
@app.route("/")
@app.route("/items")
def items_list():
    q = request.args.get("q", "").strip()

    conn = get_db()

    sql = """
    SELECT id, name, qty, unit, created_at, updated_at, is_deleted, deleted_at
    FROM items
    WHERE is_deleted = 0
    """
    params = []

    if q:
        sql += " AND name LIKE ?"
        params.append(f"%{q}%")

    sql += " ORDER BY name"

    items = conn.execute(sql, params).fetchall()
    conn.close()

    return render_template("items.html", items=items, q=q)


# -------------------------
# 商品登録（店主のみ）
# -------------------------
@app.route("/items/new", methods=["GET", "POST"])
def item_new():
    if request.method == "POST":
        passcode = request.form.get("passcode", "").strip()
        if passcode != OWNER_PASSCODE:
            abort(403, description="店主パスコードが違います。")

        name = request.form.get("name", "").strip()
        qty = request.form.get("qty", "0").strip()
        unit = request.form.get("unit", "").strip()

        if not name or not unit:
            flash("必須項目が未入力です")
            return redirect(url_for("item_new"))

        try:
            qty_int = int(qty)
        except ValueError:
            flash("数量は整数で入力してください")
            return redirect(url_for("item_new"))

        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO items (name, qty, unit, created_at, updated_at, is_deleted)
                VALUES (?, ?, ?, datetime('now'), datetime('now'), 0)
            """, (name, qty_int, unit))
            conn.commit()
        except sqlite3.IntegrityError:
            flash("同じ商品名がすでに登録されています")
            conn.close()
            return redirect(url_for("item_new"))

        conn.close()
        flash("商品を登録しました")
        return redirect(url_for("items_list"))

    return render_template("item_new.html")


# -------------------------
# 商品編集（店主のみ）※既に作ってある場合はこのままでOK
# （item_edit.html を使う想定）
# -------------------------
@app.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
def item_edit(item_id):
    conn = get_db()
    item = conn.execute("SELECT * FROM items WHERE id=? AND is_deleted=0", (item_id,)).fetchone()
    if item is None:
        conn.close()
        abort(404)

    if request.method == "POST":
        passcode = request.form.get("passcode", "").strip()
        if passcode != OWNER_PASSCODE:
            conn.close()
            abort(403, description="店主パスコードが違います。")

        name = request.form.get("name", "").strip()
        qty = request.form.get("qty", "").strip()
        unit = request.form.get("unit", "").strip()

        if not name or not unit or qty == "":
            conn.close()
            flash("必須項目が未入力です")
            return redirect(url_for("item_edit", item_id=item_id))

        try:
            qty_int = int(qty)
        except ValueError:
            conn.close()
            flash("数量は整数で入力してください")
            return redirect(url_for("item_edit", item_id=item_id))

        conn.execute("""
            UPDATE items
            SET name=?, qty=?, unit=?, updated_at=datetime('now')
            WHERE id=?
        """, (name, qty_int, unit, item_id))
        conn.commit()
        conn.close()

        flash("商品を更新しました")
        return redirect(url_for("items_list"))

    conn.close()
    return render_template("item_edit.html", item=item)


# -------------------------
# 論理削除（店主のみ）＋削除履歴
# -------------------------
@app.route("/items/<int:item_id>/delete", methods=["POST"])
def item_delete(item_id):
    passcode = request.form.get("passcode", "").strip()
    if passcode != OWNER_PASSCODE:
        abort(403, description="店主パスコードが違います。")

    conn = get_db()
    item = conn.execute("SELECT id, name, qty, unit FROM items WHERE id=? AND is_deleted=0", (item_id,)).fetchone()
    if item is None:
        conn.close()
        flash("削除対象が見つかりません")
        return redirect(url_for("items_list"))

    # 削除履歴にスナップショット保存
    conn.execute("""
        INSERT INTO item_delete_history (item_id, name, qty, unit, deleted_at)
        VALUES (?, ?, ?, ?, datetime('now'))
    """, (item["id"], item["name"], item["qty"], item["unit"]))

    # 論理削除
    conn.execute("""
        UPDATE items
        SET is_deleted=1, deleted_at=datetime('now'), updated_at=datetime('now')
        WHERE id=?
    """, (item_id,))

    conn.commit()
    conn.close()
    flash("商品を削除しました（論理削除）")
    return redirect(url_for("items_list"))


@app.route("/deleted")
def deleted():
    conn = get_db()
    histories = conn.execute("""
        SELECT history_id, item_id, name, qty, unit, deleted_at
        FROM item_delete_history
        ORDER BY history_id DESC
    """).fetchall()
    conn.close()
    return render_template("deleted.html", histories=histories)


# -------------------------
# 仕入台帳（入出庫）
# -------------------------
@app.route("/moves", methods=["GET", "POST"])
def moves():
    conn = get_db()

    items = conn.execute("""
        SELECT id, name, qty, unit
        FROM items
        WHERE is_deleted = 0
        ORDER BY name
    """).fetchall()

    if request.method == "POST":
        item_id = request.form.get("item_id")
        direction = request.form.get("direction")
        qty = request.form.get("qty", "").strip()
        note = request.form.get("note", "").strip()

        if not item_id or not direction or not qty:
            conn.close()
            flash("必須項目が未入力です")
            return redirect(url_for("moves"))

        try:
            qty_int = int(qty)
            if qty_int <= 0:
                raise ValueError
        except ValueError:
            conn.close()
            flash("数量は1以上の整数で入力してください")
            return redirect(url_for("moves"))

        cur = conn.execute("SELECT qty FROM items WHERE id = ? AND is_deleted = 0", (item_id,)).fetchone()
        if cur is None:
            conn.close()
            flash("品目が見つかりません")
            return redirect(url_for("moves"))

        current_qty = int(cur["qty"])
        new_qty = current_qty + qty_int if direction == "IN" else current_qty - qty_int

        if new_qty < 0:
            conn.close()
            flash("在庫が足りません（マイナスにはできません）")
            return redirect(url_for("moves"))

        conn.execute("""
            INSERT INTO stock_moves (item_id, direction, qty, note, happened_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (item_id, direction, qty_int, note if note else None))

        conn.execute("""
            UPDATE items
            SET qty = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (new_qty, item_id))

        conn.commit()
        conn.close()

        flash("入出庫を登録しました")
        return redirect(url_for("moves"))

    moves_list = conn.execute("""
        SELECT
          m.move_id, m.direction, m.qty, m.note, m.happened_at,
          i.name AS item_name, i.unit AS unit
        FROM stock_moves m
        JOIN items i ON m.item_id = i.id
        ORDER BY m.move_id DESC
        LIMIT 10
    """).fetchall()

    conn.close()
    return render_template("moves.html", items=items, moves=moves_list)


# -------------------------
# 担当者一覧
# -------------------------
@app.route("/users")
def users_list():
    conn = get_db()
    users = conn.execute("""
        SELECT user_id, name, role, is_active, created_at
        FROM users
        ORDER BY role, name
    """).fetchall()
    conn.close()
    return render_template("users.html", users=users)


# -------------------------
# エラーハンドラ
# -------------------------
@app.errorhandler(403)
def forbidden(e):
    return f"<h1>403</h1><p>{e.description}</p>", 403


# 起動
if __name__ == "__main__":
    app.run(debug=True, port=5001)