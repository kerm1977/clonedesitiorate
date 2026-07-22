from flask import render_template, jsonify
from models import db, Favorite, Image
from utils import get_session_id


def register_game_favorites_routes(bp):
    
    @bp.route('/favorites')
    def favorites():
        uid = get_session_id()
        favs = (Favorite.query.filter_by(user_session=uid)
                .join(Image, Favorite.image_id == Image.id)
                .add_entity(Image).all())
        return render_template('favorites.html', favs=favs)

    @bp.route('/img/<int:image_id>/favorite', methods=['POST'])
    def toggle_favorite(image_id):
        uid = get_session_id()
        fav = Favorite.query.filter_by(user_session=uid, image_id=image_id).first()
        if fav:
            db.session.delete(fav)
            db.session.commit()
        else:
            db.session.add(Favorite(user_session=uid, image_id=image_id))
            db.session.commit()
        favorited = fav is None
        count = Favorite.query.filter_by(user_session=uid).count()
        return jsonify(favorited=favorited, favorites_count=count)
