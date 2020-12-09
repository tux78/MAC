import sys, json, requests

class ForcePoint:

    def __init__(self, url, auth_key):
        self.url = url
        self.auth_key = auth_key

    def action(self, query):
        #print("Creation of the HTTP session...")
        s = requests.session()

        new_list = {"name": "bad_shared_ip", "comment": "This our new IP list"}
        new_list_content = {
            "ip": [
                query]
            }

        # Login
        #print("Login...")
        h = {'accept': 'application/json', 'content-type': 'application/json'}
        login_params = {"authenticationkey": self.auth_key}
        r = s.post(
            self.url + "login",
            data=json.dumps(login_params),
            headers=h)
        r.raise_for_status()
        #print("Login OK.")

        # Check if the IP list exists aready and create it if it doesn't
        r = s.get(self.url + "elements/ip_list", data=json.dumps(new_list), headers=h)
        r.raise_for_status()
        ip_lists = r.json()["result"]
        for entry in ip_lists:
            if entry["name"] == new_list["name"]:
                elem_url = entry["href"]
                break
        else:
            # The IP list does not exist, create it
            r = s.post(self.url + "elements/ip_list", data=json.dumps(new_list), headers=h)
            r.raise_for_status()
            #print("IP List 'new_ip_list' element created.")
            elem_url = r.headers["location"]

        # Get the element and find out content URI
        r = s.get(elem_url, headers=h)
        r.raise_for_status()
        elem_content_url = [entry["href"]
                            for entry in r.json()["link"]
                            if entry["rel"] == "ip_address_list"][0]

        # Download the content for the IP list and add new ip
        r = s.get(elem_content_url, headers=h)
        r.raise_for_status()
        #print("Retrieve the IP list content for the 'new_ip_list' element.")
        list_content = r.json()
        a = json.dumps(list_content)
        check = json.loads(a)
        new_list_content = json.loads(a)
        new_list_content['ip'].append(query)

        # Upload content for the IP list
        for ip in check['ip']:
            if ip == query:
                print("This IP is already in the SMC IP-List")
                r = s.put(self.url + "logout")
                r.raise_for_status()
                return query
            else: pass

        r = s.post(elem_content_url, data=json.dumps(new_list_content), headers=h)
        print("Added the IP to the SMC IP list.")
        r.raise_for_status()

        params= { 'filter':'HQ Policy' }
        r = s.get(self.url + 'elements/fw_policy', params=params, headers={'accept': 'application/json', 'content-type': 'application/json'})
        hq_policy_location= r.json()['result'][0]['href']
        #print("Get \'HQ Policy\' Firewall Policy URL: %s " % hq_policy_location)
        #print("Upload the 'HQ Policy' on 'Helsinki FW'...")
        r = s.post(hq_policy_location+'/upload', params=params, headers={'accept': 'application/json', 'content-type': 'application/json'})

        # Logout
        #print("Logout...")
        r = s.put(self.url + "logout")
        r.raise_for_status()
