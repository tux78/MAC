import json
import threading
from pymisp import ExpandedPyMISP

class MISP:

    def __init__(self, misp_url, misp_key, misp_verify_cert=False):

        # Initialize MISP connection
        self.misp = ExpandedPyMISP(misp_url, misp_key, misp_verify_cert)

    def process(self, sentinel : threading.Event = threading.Event(), interval : int = 300, tag_toProcess='MAC_toProcess', tag_processed='MAC_processed', **kwargs):
        while not sentinel.is_set():
            # Grab the events from MISP
            misp_result = self.misp.search(
                tags=tag_toProcess
            )

            # Process the response and events
            # Extract the MISP event details
            for e in misp_result:
                misp_event = e['Event']

                # yield the results
                yield json.dumps(misp_event, sort_keys=True)

                # Finally, update the tags on the MISP events.
                # Add a 'processed' tag to the event
                self.misp.tag(misp_event['uuid'], tag_processed)

                # Remove the 'to be processed' tag
                self.misp.untag(misp_event['uuid'], tag_toProcess)
            sentinel.wait(interval)