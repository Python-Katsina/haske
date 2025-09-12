from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

@app.route("/users/<int:user_id>")
def get_user(user_id):
    user = User.query.get(user_id)
    return jsonify({"id": user.id, "name": user.name}) if user else {}

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not User.query.get(1):
            db.session.add(User(id=1, name="Test User"))
            db.session.commit()
    app.run(debug=True, port=8000)