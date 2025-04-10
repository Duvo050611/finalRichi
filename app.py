from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import hashlib
from datetime import datetime
from flasgger import Swagger

app = Flask(__name__)
CORS(app)  # Habilita CORS para todas las rutas

# Configuración de la base de datos
db_config = {
    'host': 'database-1.ccpw8o44uuu5.us-east-1.rds.amazonaws.com',
    'user': 'admin',
    'password': '12345678',
    'db': 'database-1',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    return pymysql.connect(**db_config)

# Crear tabla de usuarios si no existe
def create_tables():
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password VARCHAR(100) NOT NULL,
                    email VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Verificar si ya existe el usuario admin
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE username = 'admin'")
            result = cursor.fetchone()
            if result['count'] == 0:
                hashed_pass = hashlib.sha256('admin123'.encode()).hexdigest()
                cursor.execute(
                    "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)",
                    ('admin', hashed_pass, 'admin@example.com')
                )
        connection.commit()
    except Exception as e:
        print(f"Error al crear tablas: {str(e)}")
        raise e
    finally:
        if connection:
            connection.close()

# Configuración de Swagger
swagger = Swagger(app)

@app.route('/login', methods=['POST'])
def login():
    """
    Login de usuario
    ---
    tags:
      - Auth
    parameters:
      - name: email
        in: body
        type: string
        required: true
        description: Correo electrónico del usuario.
      - name: password
        in: body
        type: string
        required: true
        description: Contraseña del usuario.
    responses:
      200:
        description: Login exitoso, retorna el usuario y un token.
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
            user:
              type: object
              properties:
                id:
                  type: integer
                username:
                  type: string
                email:
                  type: string
            token:
              type: string
      400:
        description: Error de credenciales inválidas.
        schema:
          type: object
          properties:
            success:
              type: boolean
            error:
              type: string
    """
    connection = None
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email y password requeridos'}), 400

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, email FROM users WHERE email = %s AND password = %s",
                (email, hashed_password)
            )
            user = cursor.fetchone()

        if user:
            return jsonify({
                'success': True,
                'message': 'Login exitoso',
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email']
                },
                'token': 'dummy-jwt-token'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Credenciales inválidas'
            }), 401

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if connection:
            connection.close()

@app.route('/register', methods=['POST'])
def register():
    """
    Registro de nuevo usuario
    ---
    tags:
      - Auth
    parameters:
      - name: username
        in: body
        type: string
        required: true
        description: Nombre de usuario del nuevo usuario.
      - name: password
        in: body
        type: string
        required: true
        description: Contraseña para el nuevo usuario.
      - name: email
        in: body
        type: string
        required: false
        description: Correo electrónico del nuevo usuario.
    responses:
      201:
        description: Usuario registrado exitosamente.
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
            user:
              type: object
              properties:
                id:
                  type: integer
                username:
                  type: string
                email:
                  type: string
      400:
        description: Error si el nombre de usuario ya existe o falta información.
        schema:
          type: object
          properties:
            success:
              type: boolean
            error:
              type: string
    """
    connection = None
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        email = data.get('email', '')

        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Username y password requeridos'
            }), 400

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)",
                (username, hashed_password, email)
            )
            user_id = cursor.lastrowid

            cursor.execute(
                "SELECT id, username, email FROM users WHERE id = %s",
                (user_id,)
            )
            new_user = cursor.fetchone()

        connection.commit()

        return jsonify({
            'success': True,
            'message': 'Usuario registrado exitosamente',
            'user': new_user
        }), 201

    except pymysql.err.IntegrityError as e:
        if "Duplicate entry" in str(e):
            return jsonify({
                'success': False,
                'error': 'El nombre de usuario ya existe'
            }), 400
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if connection:
            connection.close()

@app.route('/users', methods=['GET'])
def get_users():
    """
    Obtener todos los usuarios
    ---
    tags:
      - Users
    responses:
      200:
        description: Lista de usuarios
        schema:
          type: object
          properties:
            success:
              type: boolean
            users:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  username:
                    type: string
                  email:
                    type: string
                  created_at:
                    type: string
                    format: date-time
      500:
        description: Error al obtener los usuarios.
        schema:
          type: object
          properties:
            success:
              type: boolean
            error:
              type: string
    """
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, username, email, created_at FROM users")
            users = cursor.fetchall()

        return jsonify({
            'success': True,
            'users': users
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if connection:
            connection.close()

@app.route('/health', methods=['GET'])
def health_check():
    """
    Verificar el estado de la API
    ---
    tags:
      - Health
    responses:
      200:
        description: La API está funcionando.
        schema:
          type: object
          properties:
            status:
              type: string
              example: healthy
            timestamp:
              type: string
              format: date-time
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    }), 200
@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """
    Obtener un usuario por ID
    ---
    tags:
      - Users
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID del usuario
    responses:
      200:
        description: Usuario encontrado
      404:
        description: Usuario no encontrado
    """
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, username, email, created_at FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()

        if user:
            return jsonify({'success': True, 'user': user}), 200
        else:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if connection:
            connection.close()
            
@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """
    Actualizar un usuario por ID
    ---
    tags:
      - Users
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
            email:
              type: string
    responses:
      200:
        description: Usuario actualizado
      404:
        description: Usuario no encontrado
    """
    connection = None
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')

        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()

            if not user:
                return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

            cursor.execute(
                "UPDATE users SET username = %s, email = %s WHERE id = %s",
                (username or user['username'], email or user['email'], user_id)
            )
        connection.commit()
        return jsonify({'success': True, 'message': 'Usuario actualizado correctamente'}), 200

    except pymysql.err.IntegrityError as e:
        return jsonify({'success': False, 'error': 'Nombre de usuario ya en uso'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if connection:
            connection.close()

@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """
    Eliminar un usuario por ID
    ---
    tags:
      - Users
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID del usuario
    responses:
      200:
        description: Usuario eliminado
      404:
        description: Usuario no encontrado
    """
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()

            if not user:
                return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        connection.commit()
        return jsonify({'success': True, 'message': 'Usuario eliminado'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if connection:
            connection.close()



if __name__ == '__main__':
    create_tables()
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)