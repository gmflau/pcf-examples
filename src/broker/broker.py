import json
import os
import random
import string
import traceback

import auth
import flask
import requests

app = flask.Flask(__name__)

content_header = {'Content-Type': 'application/json; charset=utf-8'}

def get_db_configuration():
    # Return a list of [username, password, url]
    properties = [None, None, None]
    if os.getenv('SPACEBEARS_HOST') and os.getenv('SPACEBEARS_PROPERTIES'):
        # Properties as set by tile-generator from bosh link.
        link_properties = json.loads(os.getenv('SPACEBEARS_PROPERTIES'))
        url = 'http://' + os.getenv('SPACEBEARS_HOST') + ':' + str(link_properties['spacebears']['port'])
        username = link_properties['spacebears']['username']
        password = link_properties['spacebears']['password']
        properties = [username, password, url]
    # Override or set properties without bosh link.
    if os.getenv('DB_ADMIN_USERNAME'):
        properties[0] = os.getenv('DB_ADMIN_USERNAME')
    if os.getenv('DB_ADMIN_PASSWORD'):
        properties[1] = os.getenv('DB_ADMIN_PASSWORD')
    if os.getenv('DB_URL'):
        properties[2] = os.getenv('DB_URL')
    return properties

db_admin_username, db_admin_password, db_url = get_db_configuration()


def generate_random():
    charset = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return ''.join(random.SystemRandom().choice(charset) for _ in range(20))


@app.route("/health")
def health():
    return "healthy"


@app.route("/v2/catalog")
@auth.requires_auth
def broker_catalog():
    # catalog ids were randomly generated guids, per best practices
    catalog = {
        "services": [{
            "id": 'c084b262-b733-45e2-974b-ed8ad94e808a',
            "name": 'spacebears-db',
            "description": "Simple key/value services",
            "bindable": True,
            "tags": ["key-value", "spacebears"],
            "plans": [{
                "id": '30f7be98-dc0b-4fce-91bc-aeb87c864ecc',
                "name": "plan1",
                "description": "A first, free, service plan"
            }]
        }]
    }
    return json.dumps(catalog, indent=4)


@app.route("/v2/service_instances/<instance_id>", methods=['PUT'])
@auth.requires_auth
def broker_provision_instance(instance_id):
    db_api_url = "{}/api/admin/bucket/{}".format(db_url, instance_id)
    db_api_response = requests.post(
        db_api_url, auth=(db_admin_username, db_admin_password), verify=False
    )
    if db_api_response.status_code > 299:
        print(db_api_response)
        return "{}", 500, content_header
    else:
        return "{}", 201, content_header


@app.route("/v2/service_instances/<instance_id>/service_bindings/<binding_id>", methods=['PUT'])
@auth.requires_auth
def broker_bind_instance(instance_id, binding_id):
    password = generate_random()
    creds = {
        "username": binding_id,
        "password": password
    }
    db_api_url = "{}/api/admin/bucket/{}/credentials".format(db_url, instance_id)
    db_api_response = requests.put(
        db_api_url, data=json.dumps(creds), auth=(db_admin_username, db_admin_password), verify=False
    )

    if db_api_response.status_code > 299:
        print(db_api_response)
        return "{}", 500, content_header
    else:
        response_body = json.dumps({"credentials": {
            "username": binding_id,
            "password": password,
            "uri": "{}/api/bucket/{}".format(db_url, instance_id)
        }})
        return response_body, 201, content_header


@app.route("/v2/service_instances/<instance_id>/service_bindings/<binding_id>", methods=['DELETE'])
@auth.requires_auth
def broker_unbind_instance(instance_id, binding_id):
    creds = {"username": binding_id}
    db_api_url = "{}/api/admin/bucket/{}/credentials".format(db_url, instance_id)
    db_api_response = requests.delete(
        db_api_url, data=json.dumps(creds), auth=(db_admin_username, db_admin_password), verify=False
    )

    if db_api_response.status_code > 299:
        print(db_api_response)
        return "{}", 500, content_header
    else:
        response_body = json.dumps({}, indent=4)
        return response_body, 200, content_header


@app.route("/v2/service_instances/<instance_id>", methods=['DELETE'])
@auth.requires_auth
def broker_deprovision_instance(instance_id):
    db_api_url = "{}/api/admin/bucket/{}".format(db_url, instance_id)
    db_api_response = requests.delete(
        db_api_url, auth=(db_admin_username, db_admin_password), verify=False
    )
    if db_api_response.status_code > 299:
        print(db_api_response)
        return "{}", 500, content_header
    else:
        return "{}", 200, content_header


@app.errorhandler(500)
def internal_error(error):
    print(error)
    return "Internal server error", 500


if __name__ == "__main__":
    try:
        app.run(host='0.0.0.0', port=os.getenv('PORT', '8080'))
        print("Exited normally")
    except:
        print("* Exited with exception")
        traceback.print_exc()
