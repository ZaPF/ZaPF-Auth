from . import api_blueprint
from flask import request, jsonify, abort
from app.oauth2 import oauth
from app.oauth2.models import Scope

@api_blueprint.route('/api/me', methods=['GET'])
@oauth.require_oauth('ownUserData')
def apiMe():
    user = request.oauth.user
    return jsonify(
            email = user.mail,
            username = user.username,
            firstName = user.firstName,
            surname = user.surname,
            full_name = user.full_name
            )

@api_blueprint.route('/api/me/nextcloud', methods=['GET'])
@oauth.require_oauth('nextcloud')
def api_nextcloud():
    user = request.oauth.user
    if Scope.get('nextcloud') not in user.scopes:
        abort(403, 'Der Zugriff zur WolKe ist auf Gremika beschränkt und du scheinst nicht in einer Gruppe zu sein, die dir Zugriff gibt. // You are not authorized to access WolKe.')

    return jsonify(
            email = user.mail,
            user_id = user.username,
            firstName = user.firstName,
            lastName = user.surname,
            displayName = user.full_name,
            roles = [group.group_name for group in user.groups],
            )

@api_blueprint.route('/api/me/zapfwiki', methods=['GET'])
@oauth.require_oauth('ownUserData')
def api_zapfwiki():
    user = request.oauth.user

    username_buf = user.username + ' (ZaPF-Auth'
    i = user.username.find(' ')
    while i != -1:
        username_buf += ' ' + str(i)
        i = user.username.find(' ', i+1)

    username_buf += ')'

    groups = [group.group_name for group in user.groups]

    if 'admin' in groups or 'TOPF' in groups:
        wikiGroups = ['sysop', 'interface-admin', 'bureaucrat']
    elif 'StAPF' in groups or 'ZaPF e.V. Vorstand' in groups:
        wikiGroups = ['interface-admin', 'bureaucrat']
    elif 'orga' in groups or 'wikimod' in groups:
        wikiGroups = ['bureaucrat']
    else:
        wikiGroups = ['user']

    return jsonify(
            email = user.mail,
            username = username_buf,
            roles = wikiGroups,
            )
