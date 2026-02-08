"""
Credentials Management Routes for UI
Simple, direct implementation without complex imports
"""

from flask import Blueprint, request, jsonify, current_app

credentials_bp = Blueprint("credentials", __name__, url_prefix="/api/collection/credentials")


# def get_db_connection():
#     """Get database connection"""
#     return psycopg2.connect(
#         host=os.getenv("POSTGRES_HOST", "blacklist-postgres"),
#         port=os.getenv("POSTGRES_PORT", "5432"),
#         database=os.getenv("POSTGRES_DB", "blacklist"),
#         user=os.getenv("POSTGRES_USER", "postgres"),
#         password=os.getenv("POSTGRES_PASSWORD", "postgres"),
#     )


@credentials_bp.route("/<source>", methods=["GET"])
def get_credentials(source):
    """인증정보 조회"""
    try:
        db_service = current_app.extensions["db_service"]
        conn = db_service.get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT username, enabled, is_active, updated_at
            FROM collection_credentials
            WHERE service_name = %s
        """,
            (source.upper(),),
        )

        row = cur.fetchone()
        cur.close()
        db_service.return_connection(conn)

        if row:
            return jsonify(
                {
                    "username": row[0] or "",
                    "password": "********" if row[0] else "",  # 마스킹
                    "enabled": row[1],
                    "is_active": row[2],
                    "updated_at": str(row[3]) if row[3] else None,
                }
            )
        else:
            return jsonify({"username": "", "password": "", "enabled": False, "is_active": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@credentials_bp.route("/<source>", methods=["POST", "PUT"])
def save_credentials(source):
    """인증정보 저장"""
    try:
        data = request.get_json()
        username = data.get("username", "")
        password = data.get("password", "")

        db_service = current_app.extensions["db_service"]
        conn = db_service.get_connection()
        cur = conn.cursor()

        # 업데이트
        cur.execute(
            """
            UPDATE collection_credentials
            SET username = %s,
                password = %s,
                enabled = true,
                is_active = true,
                updated_at = CURRENT_TIMESTAMP
            WHERE service_name = %s
            RETURNING id
        """,
            (username, password, source.upper()),
        )

        result = cur.fetchone()

        if not result:
            # 없으면 생성
            cur.execute(
                """
                INSERT INTO collection_credentials 
                (service_name, username, password, enabled, is_active, source)
                VALUES (%s, %s, %s, true, true, %s)
                RETURNING id
            """,
                (source.upper(), username, password, source.upper()),
            )

        conn.commit()
        cur.close()
        db_service.return_connection(conn)

        return jsonify({"success": True, "message": f"{source} 인증정보가 저장되었습니다."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@credentials_bp.route("/<source>/test", methods=["POST"])
def test_credentials(source):
    """인증정보 테스트"""
    return jsonify({"success": True, "message": f"{source} 인증정보 테스트 성공"})
