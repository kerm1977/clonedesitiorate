import os
from flask import send_file, make_response, current_app


def register_game_sw_routes(bp):
    
    @bp.route('/sw.js')
    def service_worker():
        response = make_response(
            send_file(os.path.join(current_app.static_folder, 'sw.js'),
                      mimetype='application/javascript')
        )
        response.headers['Service-Worker-Allowed'] = '/'
        return response
