from ldap3 import Server, Connection, ALL_ATTRIBUTES, ALL
import os
import subprocess
import time

basedir = os.path.abspath(os.path.dirname(__file__))

data_dir = os.path.join(basedir, "OpenLDAP", "data")
config_dir = os.path.join(basedir, "OpenLDAP")
prefix = "/usr"
slapd = os.path.join(prefix, "libexec", "slapd")

# Ensure the OpenLDAP data dir exists
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# Slapadd the data
with open("data.ldif", "rb") as f:
    ldif = f.read()
slapadd = subprocess.run(
    ["slapadd", "-f", os.path.join(config_dir, "slapd.conf")],
    input=ldif,
    cwd=config_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

# Start a slapd
slapd = subprocess.Popen(
    [
        slapd,
        "-f",
        os.path.join(config_dir, "slapd.conf"),
        "-d1",
        "-h",
        "ldap://localhost:8369/",
    ],
    stdout=subprocess.PIPE,
    # stderr=subprocess.PIPE,
    cwd=config_dir,
)

# Allow the slapd to start
time.sleep(30)

print(slapd)

# Get the info we need
server = Server("localhost", port=8369, get_info=ALL)
connection = Connection(
    server, "uid=root,dc=my-domain,dc=com", "secret", auto_bind=True
)
if connection.search(
    "dc=my-domain,dc=com", "(objectclass=*)", attributes=ALL_ATTRIBUTES
):
    connection.response_to_file("entries.json", raw=True)

server.schema.to_file("schema.json")
server.info.to_file("info.json")

# kill the slapd again
slapd.kill()
