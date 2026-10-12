from datetime import datetime, timezone

from app import db


class Student(db.Model):
    __tablename__ = 'students'
    __table_args__ = (
        db.UniqueConstraint('email', name='uq_students_email'),
        db.CheckConstraint('email = lower(email)', name='ck_students_email_lower'),
    )

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    group = db.Column(db.String(40), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc), server_default=db.func.now())

    def to_dict(self):
        return {key: getattr(self, key) for key in ('id', 'first_name', 'last_name', 'email', 'group')} | {
            'created_at': self.created_at.isoformat(),
        }
