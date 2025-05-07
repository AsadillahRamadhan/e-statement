from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from zoneinfo import ZoneInfo


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(11), nullable=False)

    @property
    def password(self):
        raise AttributeError("Password is write-only.")

    @password.setter
    def password(self, plain_text):
        self.password_hash = generate_password_hash(plain_text)

    def verify_password(self, plain_text):
        return check_password_hash(self.password_hash, plain_text)

class TransferUser(db.Model):
    __tablename__ = "transfer_users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    account_number = db.Column(db.String(25), nullable=False)
    bank_name = db.Column(db.String(10), nullable=False)

class BankCode(db.Model):
    __tablename__ = "bank_codes"
    id = db.Column(db.Integer, primary_key=True)
    bank_name = db.Column(db.String(100), nullable=False)
    bank_code = db.Column(db.String(3), nullable=False)

class ConverterLog(db.Model):
    __tablename__ = "converter_logs"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    nik = db.Column(db.String(16), nullable=False)
    mobile_phone = db.Column(db.String(15), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    files = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("Asia/Jakarta")))
