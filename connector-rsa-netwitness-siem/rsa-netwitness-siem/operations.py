import requests

from connectors.core.connector import get_logger, ConnectorError
from connectors.core.connector import Connector

logger = get_logger('rsa-netwitness-siem')

messages_codes = {
    400: 'Invalid input',
    401: 'Unauthorized: Invalid credentials',
    500: 'Invalid input',
    404: 'Invalid input',
    'ssl_error': 'SSL certificate validation failed',
    'timeout_error': 'The request timed out while trying to connect to the remote server'
}


class NetwitnessSIEM():
    def __init__(self, config):
        self.server_url = config.get('server_url')
        if self.server_url.startswith('https://') or self.server_url.startswith('http://'):
            self.server_url = self.server_url.strip('/')
        else:
            self.server_url = 'http://{0}'.format(self.server_url)
        self.username = config.get('username')
        self.password = config.get('password')
        self.accessToken = None
        self.verify_ssl = config.get('verify_ssl')

    def make_api_call(self, method='GET', headers=None, updated_headers=None, endpoint=None, params=None, data=None,
                      json=None):
        if updated_headers:
            self.generate_token()
            updated_headers.update({"NetWitness-Token": self.accessToken})
            headers = dict()
            headers.update(updated_headers)
        if endpoint:
            url = '{0}{1}'.format(self.server_url, endpoint)
        else:
            url = '{0}'.format(self.server_url)

        logger.info('Request URL {}'.format(url))
        try:
            response = requests.request(method=method, url=url, params=params, data=data, json=json, headers=headers,
                                        verify=self.verify_ssl)
            if response.ok:
                if response.status_code == 204:
                    return {"Status": "Success", "Message": "Executed successfully"}
                result = response.json()
                return result
            elif messages_codes[response.status_code]:
                logger.error('{}'.format(messages_codes[response.status_code]))
                raise ConnectorError('{}'.format(messages_codes[response.status_code]))
            else:
                logger.error(
                    'Fail To request API {0} response is : {1} with reason: {2}'.format(str(url), str(response.content),
                                                                                        str(response.reason)))
                raise ConnectorError(
                    'Fail To request API {0} response is :{1} with reason: {2}'.format(str(url), str(response.content),

                                                                                       str(response.reason)))

        except requests.exceptions.SSLError as e:
            logger.exception('{}'.format(e))
            raise ConnectorError('{}'.format(messages_codes['ssl_error']))
        except requests.exceptions.ConnectionError as e:
            logger.exception('{}'.format(e))
            raise ConnectorError('{}'.format(messages_codes['timeout_error']))
        except Exception as e:
            logger.exception('{}'.format(e))
            raise ConnectorError('{}'.format(e))

    def generate_token(self):
        try:
            headers = {"Accept": "application/json;charset=UTF-8",
                       "Content-Type": "application/x-www-form-urlencoded; charset=ISO-8859-1"}
            response = self.make_api_call(headers=headers,
                                          method='POST', endpoint='/rest/api/auth/userpass',
                                          data="username={username}&password={password}".
                                          format(username=self.username, password=self.password))
            if response:
                self.accessToken = response.get('accessToken')
                return True
            else:
                raise ConnectorError(
                    "Exception occured: {} with status code: {}".format(response.reason, response.status_code))
        except Exception as err:
            logger.error("{}".format(str(err)))
            raise ConnectorError("{}".format(str(err)))


def build_payload(params):
    result = {k: v for k, v in params.items() if v is not None and v != ''}
    return result


def check_health(config):
    obj = NetwitnessSIEM(config)
    try:
        if obj.generate_token():
            return True
        else:
            logger.exception('Error occured while connecting server')
            raise ConnectorError('Error occured while connecting server')
    except Exception as Err:
        logger.exception('Error occured while connecting server: {}'.format(str(Err)))
        raise ConnectorError('Error occured while connecting server: {}'.format(Err))


def get_incident(config, params):
    try:
        obj = NetwitnessSIEM(config)
        response = obj.make_api_call(
            updated_headers={"Accept": "application/json;charset=UTF-8"},
            endpoint="/rest/api/incidents/{id}".format(id=params.get('id')))
        return response
    except Exception as Err:
        logger.error('Exception occurred: {}'.format(Err))
        raise ConnectorError(Err)


def get_incident_by_date_range(config, params):
    try:
        obj = NetwitnessSIEM(config)
        payload = build_payload(params)
        if payload:
            response = obj.make_api_call(updated_headers={"Accept": "application/json;charset=UTF-8"},
                                         endpoint="/rest/api/incidents", params=payload)
        else:
            response = obj.make_api_call(updated_headers={"Accept": "application/json;charset=UTF-8"},
                                         endpoint="/rest/api/incidents")
        return response
    except Exception as Err:
        logger.error('Exception occurred: {}'.format(Err))
        raise ConnectorError(Err)


def get_incidents_alerts(config, params):
    try:
        obj = NetwitnessSIEM(config)
        payload = build_payload(params)
        payload.pop('id')
        response = obj.make_api_call(
            updated_headers={"Accept": "application/json;charset=UTF-8"},
            endpoint="/rest/api/incidents/{id}/alerts".format(id=params.get('id')), params=payload)
        return response
    except Exception as Err:
        logger.error('Exception occurred: {}'.format(Err))
        raise ConnectorError(Err)


operations = {'get_incident': get_incident,
              'get_incident_by_date_range': get_incident_by_date_range,
              'get_incidents_alerts': get_incidents_alerts
              }
