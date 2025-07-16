import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, redirect, render_template
from flask_cors import CORS
from models import ShortURL
from database import db, init_db
import shortuuid

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///urls.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

init_db(app)

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/shorten', methods=['POST'])
def create_short_url():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL is required'}), 400

    if not data['url'].startswith(('http://', 'https://')):
        return jsonify({'error': 'URL must start with http:// or https://'}), 400

    short_code = shortuuid.ShortUUID().random(length=6)
    if ShortURL.query.filter_by(short_code=short_code).first():
        return jsonify({'error': 'Generated short code already exists'}), 409

    new_url = ShortURL(original_url=data['url'], short_code=short_code)
    db.session.add(new_url)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error: ' + str(e)}), 500

    return jsonify(new_url.to_dict()), 201

@app.route('/shorten/<short_code>', methods=['GET'])
def get_original_url(short_code):
    url_entry = ShortURL.query.filter_by(short_code=short_code).first()
    if not url_entry:
        return jsonify({'error': 'URL not found'}), 404

    url_entry.access_count += 1
    db.session.commit()
    return jsonify(url_entry.to_dict()), 200

@app.route('/shorten/<short_code>/stats', methods=['GET'])
def get_url_stats(short_code):
    url_entry = ShortURL.query.filter_by(short_code=short_code).first()
    if not url_entry:
        return jsonify({'error': 'URL not found'}), 404

    return jsonify(url_entry.to_dict()), 200

@app.route('/shorten/<short_code>', methods=['PUT'])
def update_short_url(short_code):
    url_entry = ShortURL.query.filter_by(short_code=short_code).first()
    if not url_entry:
        return jsonify({'error': 'URL not found'}), 404

    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL is required'}), 400

    if not data['url'].startswith(('http://', 'https://')):
        return jsonify({'error': 'URL must start with http:// or https://'}), 400

    url_entry.original_url = data['url']
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error: ' + str(e)}), 500

    return jsonify(url_entry.to_dict()), 200

@app.route('/shorten/<short_code>', methods=['DELETE'])
def delete_short_url(short_code):
    url_entry = ShortURL.query.filter_by(short_code=short_code).first()
    if not url_entry:
        return jsonify({'error': 'URL not found'}), 404

    try:
        db.session.delete(url_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error: ' + str(e)}), 500

    return '', 204

@app.route('/<short_code>')
def redirect_to_original(short_code):
    url_entry = ShortURL.query.filter_by(short_code=short_code).first()
    if not url_entry:
        return jsonify({'error': 'URL not found'}), 404

    url_entry.access_count += 1
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error: ' + str(e)}), 500

    return redirect(url_entry.original_url, code=301)

@app.route('/links')
def list_links():
    all_urls = ShortURL.query.all()
    return jsonify([url.to_dict() for url in all_urls])

if __name__ == '__main__':
    app.run(debug=True)
