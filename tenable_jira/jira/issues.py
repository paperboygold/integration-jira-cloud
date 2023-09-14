from restfly.endpoint import APIEndpoint

class IssuesAPI(APIEndpoint):
    def get_field_id(self, field_name):
        # If the field ID is already stored, return it
        if hasattr(self, '_field_ids') and field_name in self._field_ids:
            return self._field_ids[field_name]

        # Otherwise, get the field ID from the API
        response = self._api.get('field')

        # If the response is a requests.Response object, get the JSON data
        if hasattr(response, 'json'):
            fields = response.json()
        else:
            fields = response

        for field in fields:
            if field['name'] == field_name:
                # Store the field ID in an instance variable
                if not hasattr(self, '_field_ids'):
                    self._field_ids = {}
                self._field_ids[field_name] = field['id']
                return field['id']

        return None

    def replace_spaces_in_device_hostname(self, **kwargs):
        # Get the field id for 'Device Hostname'
        device_hostname_field_id = self.get_field_id('Device Hostname')

        # If there's a 'fields' dict and it has a 'Device Hostname' key
        if 'fields' in kwargs and device_hostname_field_id in kwargs['fields']:
            # If 'Device Hostname' is a list
            if isinstance(kwargs['fields'][device_hostname_field_id], list):
                kwargs['fields'][device_hostname_field_id] = [
                    item.replace(' ', '_') for item in kwargs['fields'][device_hostname_field_id]
                ]
            # If 'Device Hostname' is not a list
            else:
                kwargs['fields'][device_hostname_field_id] = kwargs['fields'][device_hostname_field_id].replace(' ', '_')

        return kwargs

    def search_validate(self, issue_ids, *jql):
        return self._api.post('jql/match', json={
            'issueIds': list(issue_ids),
            'jqls': list(jqls)
        }).json()

    def search(self, jql, **kwargs):
        kwargs['jql'] = jql
        return self._api.post('search', json=kwargs).json()

    def details(self, id, **kwargs):
        return self._api.get('issue/{}'.format(id), params=kwargs).json()

    def create(self, update_history=False, **kwargs):
        kwargs = self.replace_spaces_in_device_hostname(**kwargs)

        return self._api.post('issue',
            params={'update_history': update_history},
            json=kwargs
        ).json()

    def update(self, id, **kwargs):
        params = {
            'notifyUsers': str(kwargs.pop('notifyUsers', True)).lower(),
            'overrideScreenSecurity': str(kwargs.pop('overrideScreenSecurity', False)).lower(),
            'overrideEditableFlag': str(kwargs.pop('overrideEditableFlag', False)).lower(),
        }

        kwargs = self.replace_spaces_in_device_hostname(**kwargs)

        return self._api.put('issue/{}'.format(id),
            params=params, json=kwargs)

    def get_transitions(self, id):
        return self._api.get('issue/{}/transitions'.format(id)).json()

    def transition(self, id, **kwargs):
        return self._api.post('issue/{}/transitions'.format(id), json=kwargs)

    def upsert(self, **kwargs):
        jql = kwargs.pop('jql')
        resp = self.search(jql)
        if resp['total'] > 0:
            issue = resp['issues'][0]
            self._log.info('UPDATED {} {}'.format(
                issue['key'], issue['fields']['summary']))
            self.update(issue['id'], **kwargs)
            return issue
        else:
            issue = self.create(**kwargs)
            self._log.info('CREATED {} {}'.format(
                issue['key'], kwargs['fields']['summary']))
            return issue