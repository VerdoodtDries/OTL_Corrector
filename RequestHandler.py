import json

from requests import Response
from requests.exceptions import ConnectionError


class RequestHandler:
    def __init__(self, requester):
        self.requester = requester

    def get_jsondict(self, url):
        response = self.perform_get_request(url)
        decoded_string = response.content.decode("utf-8")
        return json.loads(decoded_string)

    def perform_get_request(self, url) -> Response:
        response = self.requester.get(url=url)
        if str(response.status_code)[:1] != '2':
            raise ConnectionError(f'status {response.status_code}')
        return response

    def perform_post_request(self, url, json_data=None, **kwargs) -> Response:
        if json_data is not None:
            kwargs['json'] = json_data
        response = self.requester.post(url=url, **kwargs)
        if str(response.status_code)[:1] != '2':
            raise ConnectionError(f'status {response.status_code}')
        return response

    def perform_put_request(self, url, json_data=None, **kwargs) -> Response:
        """
        NEW method: PUT

        :param url:
        :param json_data:
        :param kwargs:
        :return:
        """
        if json_data is not None:
            kwargs['json'] = json_data
        response = self.requester.put(url=url, **kwargs)
        if str(response.status_code)[:1] != '2':
            raise ConnectionError(f'status {response.status_code}')
        return response
