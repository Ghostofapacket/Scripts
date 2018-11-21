#!/usr/bin/env python
#title           :microsoft_azure_route_server.py
#description     :Automatic update script for Microsoft Online services (Office 365 / Exchange Online etc)
#author          :Matt Iggo - matt@iggo.co.uk
#date            :21-11-2018
#version         :0.1
#usage           :python3 microsoft_azure_route_server.py
#notes           :Ammend as required, Shown is for a pair of ASA firewalls. Check the documentation for netmiko for easy configurations
#python_version  :3.7.1
#==============================================================================

# Import the modules needed to run the script.
from netmiko import ConnectHandler
import json
import os
import urllib.request
import uuid
import socket
import difflib
import time
import sys
import datetime

# Get current time for logging
now = datetime.datetime.now()
scriptstarttime = now.strftime("%H-%M-%S")

# Define the device login details

asa1_cisco_asa = {
'device_type': 'cisco_asa',
'ip': '1.1.1.1',
'username': 'routeserver',
'password': 'somepassword',
'secret': 'somepassword',
'verbose': False,
}

asa2_cisco_asa = {
'device_type': 'cisco_asa',
'ip': '1.1.1.2',
'username': 'routeserver',
'password': 'FJmGsaqX9r7LZMdcTcKgBSzFCgWYqnqh',
'secret': 'FJmGsaqX9r7LZMdcTcKgBSzFCgWYqnqh',
'verbose': False,
}

# helper to call the webservice and parse the response
def webApiGet(methodName, instanceName, clientRequestId):
    ws = "https://endpoints.office.com"
    requestPath = ws + '/' + methodName + '/' + instanceName + '?clientRequestId=' + clientRequestId
    request = urllib.request.Request(requestPath)
#    print(requestPath)
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode())

def len2mask(len):
    """Convert a bit length to a dotted netmask (aka. CIDR to netmask)"""
    mask = ''
    if not isinstance(len, int) or len < 0 or len > 32:
        print
        "Illegal subnet length: %s (which is a %s)" % (str(len), type(len).__name__)
        return None

    for t in range(4):
        if len > 7:
            mask += '255.'
        else:
            dec = 255 - (2 ** (8 - len) - 1)
            mask += str(dec) + '.'
        len -= 8
        if len < 0:
            len = 0

    return mask[:-1]

def writelog(message):
    with open("routeserver.log", "a") as myfile:
         message = message + "\n"
         myfile.write(message)

try:
    fn = open('routeconfig.txt', 'r')
except:
    file_name = 'routeconfig.txt'
    file = open(file_name, 'a+')  # open file in append mode
    file.close()


# path where client ID and latest version number will be stored
datapath = 'endpoints_clientid_latestversion.txt'

# Get the DNS response for endpoints.office.com and check to see if it's still accurate. If it's not, Update it and change it on the ASA
endpointsaddress = socket.gethostbyname('endpoints.office.com')
while True:
    print('\n',
    ' ******************************************************************************************* \n'
    '                                 SCRIPT IS STARTING                                          \n'
    ' ******************************************************************************************* \n')
    writelog(now.strftime("%Y-%m-%d %H:%M:%S"))
    # Get the DNS entry for endpoints.office.com and make sure it's routed out the ASA
    if os.path.exists('endpoints.office.com.txt'):
        with open('endpoints.office.com.txt', 'r') as officednstext:
            fileofficeaddress = officednstext.readline().strip()
            if endpointsaddress == fileofficeaddress:
                currentdnsmessage = 'Current DNS entry for endpoints.office.com is ' + endpointsaddress + ' Which already routed out of the internet links'
                writelog(currentdnsmessage)
                print(currentdnsmessage)
            else:
                # Write out the endpoint IP address for cleanup later (should the script not be able to remove them)
                currentdnsmessage = 'Current DNS entry for endpoints.office.com is ' + fileofficeaddress + ' Which has changed to' + endpointsaddress + ' Setting the routes...'
                writelog(currentdnsmessage)
                print(currentdnsmessage)
                with open('endpoints.office.com.txt', 'w') as officednstext:
                    endpointwrite = endpointsaddress + '\n'
                    officednstext.write(endpointwrite)
                # Login to the Cisco ASA and remove the old IP
                #Connect to the asa1 ASA
                asa1_net_connect = ConnectHandler(**asa1_cisco_asa)
                #Enter enable mode
                asa1_net_connect.enable()
                #Insert the route into the ASA
                asa1_net_connect.send_config_set("route OUTSIDE " + endpointsaddress + " 255.255.255.255 x.x.x.x 15")
                asa1_net_connect.send_command("write memory")
                asa1_net_connect.disconnect()

                # Connect to the asa2 ASA
                asa2_net_connect = ConnectHandler(**asa2_cisco_asa)
                # Enter enable mode
                asa2_net_connect.enable()
                # Insert the route into the ASA
                asa2_net_connect.send_config_set("route outside " + endpointsaddress + " 255.255.255.255 x.x.x.x 15")
                asa2_net_connect.send_command("write memory")
                asa2_net_connect.disconnect()
                pausemessage = now.strftime("%Y-%m-%d %H:%M:%S"), 'Pausing here for 30 seconds to allow route propegation'
                print(pausemessage)
                writelog(pausemessage)
                for remaining in range (29, -1, -1):
                    sys.stdout.write("\r")
                    sys.stdout.write("{:2d} seconds remaining.".format(remaining))
                    sys.stdout.flush()
                    time.sleep(1)
                print(" \n")

    else:
        print('No known current IP for endpoints.office.com... Adding')
        writelog('No known current IP for endpoints.office.com... Adding')
        with open('endpoints.office.com.txt', 'w') as officednstext:
            officednstext.write(endpointsaddress)
        print('DNS resolved endpoints.office.com to', endpointsaddress)
        writelog('DNS resolved endpoints.office.com to' + endpointsaddress)
        print('Configuring route on asa1 Cisco ASA')
        writelog('Configuring route on asa1 Cisco ASA')
        # Login to the Cisco ASA and remove the old IP
        #Connect to the asa1 ASA
        asa1_net_connect = ConnectHandler(**asa1_cisco_asa)
        #Enter enable mode
        asa1_net_connect.enable()
        #Insert the route into the ASA
        asa1_net_connect.send_config_set("route OUTSIDE " + endpointsaddress + " 255.255.255.255 x.x.x.x 15")
        asa1_net_connect.send_command("write memory")
        asa1_net_connect.disconnect()

        print('Configuring route on asa2 Cisco ASA')
        writelog('Configuring route on asa2 Cisco ASA')
        # Connect to the asa2 ASA
        asa2_net_connect = ConnectHandler(**asa2_cisco_asa)
        # Enter enable mode
        asa2_net_connect.enable()
        # Insert the route into the ASA
        asa2_net_connect.send_config_set("route outside " + endpointsaddress + " 255.255.255.255 x.x.x.x 15")
        asa2_net_connect.send_command("write memory")
        asa2_net_connect.disconnect()

        print('Pausing here for 30 seconds to allow route propegation')
        writelog('Pausing here for 30 seconds to allow route propegation')
        for remaining in range (29, -1, -1):
            sys.stdout.write("\r")
            sys.stdout.write("{:2d} seconds remaining.".format(remaining))
            sys.stdout.flush()
            time.sleep(1)

    print(" \n")


    # fetch client ID and version if data exists; otherwise create new file
    if os.path.exists(datapath):
        with open(datapath, 'r') as fin:
            clientRequestId = fin.readline().strip()
            latestVersion = fin.readline().strip()
    else:
        clientRequestId = str(uuid.uuid4())
        latestVersion = '0000000000'
        with open(datapath, 'w') as fout:
            fout.write(clientRequestId + '\n' + latestVersion)

    # call version method to check the latest version, and pull new data if version number is different
    version = webApiGet('version', 'Worldwide', clientRequestId)
    print(now.strftime("%Y-%m-%d %H:%M:%S"), 'Getting route data from Office365 Commercial Service')
    if version['latest'] > latestVersion:
        print('New version of Office 365 worldwide commercial service instance endpoints detected')
        writelog('New version of Office 365 worldwide commercial service instance endpoints detected')
        # write the new version number to the data file
        with open(datapath, 'w') as fout:
            fout.write(clientRequestId + '\n' + version['latest'])

        # invoke endpoints method to get the new data
        endpointSets = webApiGet('endpoints', 'Worldwide', clientRequestId)
        # filter results for Allow and Optimize endpoints, and transform these into tuples with port and category
        flatIps = []
        for endpointSet in endpointSets:
            if endpointSet['category'] in ('Optimize', 'Allow'):
                ips = endpointSet['ips'] if 'ips' in endpointSet else []
                category = endpointSet['category']
                # IPv4 strings have dots while IPv6 strings have colons
                ip4s = [ip for ip in ips if '.' in ip]
                flatIps.extend([(category, ip) for ip in ip4s])

        # print(','.join(sorted(set([ip for (category, ip) in flatIps]))))
        Ipslist = str(','.join(sorted(set([ip for (category, ip) in flatIps]))))
        iparray = Ipslist.split(",")
        #print(iparray)
        #print("\n".join(iparray))
        command = str("\n".join(iparray))
        #print(command)
        # write the new version number to the data file
        with open("iplist.txt", 'w') as fout:
            fout.write(command)
        #print(re.split(r',(?=")', Ipslist))

        route_array = []
        with open("iplist.txt") as sourcefile:
            for line in sourcefile:
                route_array.append(line)

        linecount = sum(1 for line in open("iplist.txt"))
        for linecount in range(0, linecount):
            line = route_array[linecount].lstrip()
            subnetline = route_array[linecount].lstrip().rstrip()
            subnetmask = subnetline.split("/")
            if subnetmask[1] == "32":
                convertedmask = "255.255.255.255"
            if subnetmask[1] == "31":
                convertedmask = "255.255.255.254"
            if subnetmask[1] == "30":
                convertedmask = "255.255.255.252"
            if subnetmask[1] == "29":
                convertedmask = "255.255.255.248"
            if subnetmask[1] == "28":
                convertedmask = "255.255.255.240"
            if subnetmask[1] == "27":
                convertedmask = "255.255.255.224"
            if subnetmask[1] == "26":
                convertedmask = "255.255.255.192"
            if subnetmask[1] == "25":
                convertedmask = "255.255.255.128"
            if subnetmask[1] == "24":
                convertedmask = "255.255.255.0"
            if subnetmask[1] == "23":
                convertedmask = "255.255.254.0"
            if subnetmask[1] == "22":
                convertedmask = "255.255.252.0"
            if subnetmask[1] == "21":
                convertedmask = "255.255.248.0"
            if subnetmask[1] == "20":
                convertedmask = "255.255.240.0"
            if subnetmask[1] == "19":
                convertedmask = "255.255.224.0"
            if subnetmask[1] == "18":
                convertedmask = "255.255.192.0"
            if subnetmask[1] == "17":
                convertedmask = "255.255.128.0"
            if subnetmask[1] == "16":
                convertedmask = "255.255.0.0."
            if subnetmask[1] == "15":
                convertedmask = "255.254.0.0"
            if subnetmask[1] == "14":
                convertedmask = "255.252.0.0"
            if subnetmask[1] == "13":
                convertedmask = "255.248.0.0"
            if subnetmask[1] == "12":
                convertedmask = "255.240.0.0"
            if subnetmask[1] == "11":
                convertedmask = "255.224.0.0"
            if subnetmask[1] == "10":
                convertedmask = "255.192.0.0"
            if subnetmask[1] == "9":
                convertedmask = "255.128.0.0"
            if subnetmask[1] == "8":
                convertedmask = "255.0.0.0"
            configline = subnetmask[0] + " " + convertedmask + "\n"

            with open("routeconfig_new.txt", 'a') as fout:
                fout.write(configline)
        with open('routeconfig.txt') as currentroutes, open('routeconfig_new.txt') as newroutes:
            diff = difflib.ndiff(currentroutes.readlines(), newroutes.readlines())
        with open('routediff.txt', 'w') as result:
            for line in diff:
                result.write(line)
    #    print(now.strftime("%Y-%m-%d %H:%M:%S"), 'Configuring Cisco ASAs')
        with open('routediff.txt', 'r') as routefile:
            for line in routefile:
                if line.startswith("-"):
                    writelog('Removed the following routes')
                    print('\n Removed the following routes')
                    routestatement = line[2:]
                    routestatement = routestatement.rstrip()
                    # Login to the Cisco ASA and remove the old route
                    # Connect to the asa1 ASA
                    asa1_net_connect = ConnectHandler(**asa1_cisco_asa)
                    # Enter enable mode
                    asa1_net_connect.enable()
                    # Remove the route from the ASA
                    print(now.strftime("%Y-%m-%d %H:%M:%S"), '- asa1 '
                         'no route OUTSIDE ' + routestatement + ' x.x.x.x 15')
                    writelog(now.strftime("%Y-%m-%d %H:%M:%S") + '- asa1 no route OUTSIDE ' + routestatement + ' x.x.x.x 15')
                    asa1_net_connect.send_config_set("no route OUTSIDE " + routestatement + " x.x.x.x 15")
                    # Connect to the asa2 ASA
                    asa2_net_connect = ConnectHandler(**asa2_cisco_asa)
                    # Enter enable mode
                    asa2_net_connect.enable()
                    # Insert the route into the ASA
                    print(now.strftime("%Y-%m-%d %H:%M:%S"), '- asa2 '
                         'no route outside ' + routestatement  + ' x.x.x.x 15')
                    writelog(now.strftime("%Y-%m-%d %H:%M:%S") + '- asa2 no route outside ' + routestatement  + ' x.x.x.x 15')
                    asa2_net_connect.send_config_set("no route outside " + routestatement  + " x.x.x.x 15")

                elif line.startswith("+"):
                    print('\n Added the following routes')
                    routestatement = line[2:]
                    routestatement = routestatement.rstrip()
                    # Login to the Cisco ASA and add the new route
                    # Connect to the asa1 ASA
                    asa1_net_connect = ConnectHandler(**asa1_cisco_asa)
                    # Enter enable mode
                    asa1_net_connect.enable()
                    # Remove the route from the ASA
                    print(now.strftime("%Y-%m-%d %H:%M:%S"), '- asa1 '
                         'route OUTSIDE ' + routestatement + ' x.x.x.x 15')
                    writelog(now.strftime("%Y-%m-%d %H:%M:%S") + '- asa1 route OUTSIDE ' + routestatement + ' x.x.x.x 15')
                    asa1_net_connect.send_config_set("route OUTSIDE " + routestatement + " x.x.x.x 15")
                    # Connect to the asa2 ASA
                    asa2_net_connect = ConnectHandler(**asa2_cisco_asa)
                    # Enter enable mode
                    asa2_net_connect.enable()
                    # Insert the route into the ASA
                    print(now.strftime("%Y-%m-%d %H:%M:%S"), '- asa2 '
                         'route outside ' + routestatement  + ' x.x.x.x 15')
                    writelog(now.strftime("%Y-%m-%d %H:%M:%S") + '- asa2 route outside ' + routestatement  + ' x.x.x.x 15')
                    asa2_net_connect.send_config_set(" route outside " + routestatement  + " x.x.x.x 15")

        # Write configuration onto ASA devices & disconnect
        # Connect to the asa1 ASA
        asa1_net_connect = ConnectHandler(**asa1_cisco_asa)
        # Enter enable mode
        asa1_net_connect.enable()
        asa1_net_connect.send_command("write memory")
        asa1_net_connect.disconnect()
        # Connect to the asa2 ASA
        asa2_net_connect = ConnectHandler(**asa2_cisco_asa)
        # Enter enable mode
        asa2_net_connect.enable()
        asa2_net_connect.send_command("write memory")
        asa2_net_connect.disconnect()

        # remove old routes file
        os.remove("routeconfig.txt")
        # rename new routes file
        os.rename("routeconfig_new.txt", "routeconfig.txt")
        # cleaup ip file
        os.remove("iplist.txt")
        # cleanup diff file
        os.remove("routediff.txt")

    else:
        print('Office 365 worldwide commercial service instance endpoints are up-to-date')
        writelog(now.strftime("%Y-%m-%d %H:%M:%S") + ' - Office 365 worldwide commercial service instance endpoints are up-to-date')

    print('\n Pausing for 5 minutes')
    writelog('Pausing for 5 minutes')
    for remaining in range (299, -1, -1):
       sys.stdout.write("\r")
       sys.stdout.write("{:2d} seconds remaining.".format(remaining))
       sys.stdout.flush()
       time.sleep(1)
