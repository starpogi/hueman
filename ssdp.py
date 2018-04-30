import socket
# import urllib2
# import urlparse
# from xml.dom import minidom
import re


def SSDP_to_dict(response):
    data_payload = {}
    response = response.decode('UTF-8')

    for fragment in response.split("\r\n"):
        parts = fragment.split(":")

        if len(parts) > 1:
            data_payload.update({parts[0]: ':'.join(parts[1:]).strip()})

    return data_payload


def find_bridge():
    hosts = []
    target_host = None
    target_port = None

    path_re = re.compile("^http(s*)\:\/\/(?P<host>(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}))\:*(?P<port>\d*)(?P<path>.*)")

    msg = b"M-SEARCH * HTTP/1.1 \r\n" \
        b"HOST:239.255.255.250:1900\r\n" \
        b"ST:upnp:rootdevice\r\nMX:2\r\n" \
        b"MAN:ssdp:discover\r\n" \
        b"\r\n"

    # Set up UDP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.settimeout(2)
    s.sendto(msg, ('239.255.255.250', 1900))

    try:
        while True:
            data, addr = s.recvfrom(65507)
            hosts.append(SSDP_to_dict(data))
    except socket.timeout:
        pass

    if not hosts:
        return None, None

    for host in hosts:
        if 'hue-bridgeid' in host:
            search_groups = path_re.search(host['LOCATION'])

            if search_groups is not None:
                target_host = search_groups.group('host')
                target_port = search_groups.group('port')

    return target_host, target_port


# def XMLGetNodeText(node):
#     """
#     Return text contents of an XML node.
#     """
#     text = []
#     for childNode in node.childNodes:
#         if childNode.nodeType == node.TEXT_NODE:
#             text.append(childNode.data)
#     return(''.join(text))
#
#
# def get_XML(location):
#
#     # Fetch SCPD
#     response = urllib2.urlopen(location)
#     root_xml = minidom.parseString(response.read())
#     response.close()
#
#     # Construct BaseURL
#     base_url_elem = root_xml.getElementsByTagName('URLBase')
#     if base_url_elem:
#         base_url = XMLGetNodeText(base_url_elem[0]).rstrip('/')
#     else:
#         url = urlparse.urlparse(location)
#         base_url = '%s://%s' % (url.scheme, url.netloc)
#
#     # Output Service info
#     for node in root_xml.getElementsByTagName('service'):
#         service_type = XMLGetNodeText(node.getElementsByTagName('serviceType')[0])
#         control_url = '%s%s' % (
#             base_url,
#             XMLGetNodeText(node.getElementsByTagName('controlURL')[0])
#         )
#         scpd_url = '%s%s' % (
#             base_url,
#             XMLGetNodeText(node.getElementsByTagName('SCPDURL')[0])
#         )
#         print('%s:\n  SCPD_URL: %s\n  CTRL_URL: %s\n' % (service_type,
#                                                          scpd_url,
#                                                          control_url))
