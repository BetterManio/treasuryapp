from flask import Blueprint

bp = Blueprint("yields", __name__)

from app.yields import routes
