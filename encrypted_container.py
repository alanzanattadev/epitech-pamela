#!/usr/bin/python3
import os
import subprocess
import json
from subprocess import call
import random

def execShellCommand(command):
    if 'PAM_TYPE' in os.environ:
        return subprocess.check_output(command, shell=True)
    else:
        print(command)

def getConfiguration(path):
    print("reading configuration")
    if os.path.isfile(path):
        with open(path, 'r') as data_file:
            return json.load(data_file)
    else:
        return {}

def saveConfiguration(configuration, path):
    print("saving configuration")
    with open(path, 'w') as data_file:
        data_file.write(json.dumps(configuration))
    execShellCommand("chmod 600 " + path)

def getUserConfiguration(configuration, username):
    if username in configuration:
        return configuration[username]
    else:
        return None

def isUserConfigured(username):
    if getUserConfiguration(username) != None:
        return False
    else:
        return True

def addUserConfiguration(configuration, username, partition, passwordPath):
    configuration[username] = {"partition": partition, "password_path": passwordPath}


def getPartitionInUserConfiguration(config):
    return config['partition']

def getPasswordPathInUserConfiguration(config):
    return config['password_path']

def formatLuks(partition, username, password):
    execShellCommand("echo '" + password + "' | cryptsetup luksFormat -c aes -h sha256 " + partition)

def openLuks(partition, username, password):
    execShellCommand("echo '" + password + "' | cryptsetup luksOpen " + partition + " " + username)

def createContainer(partition, username):
    execShellCommand("mkfs.ext3 /dev/mapper/" + username)

def getGroupNameOfUser(username):
    name = execShellCommand("id -g -n " + username)
    return name or "alan"

def openContainer(partition, username):
    execShellCommand("mkdir -p /home/" + username + "/secret")
    execShellCommand("mount -t ext3 /dev/mapper/" + username + " /home/" + username + "/secret")
    execShellCommand("chown -R " + username + ":" + getGroupNameOfUser(username))

def getNewPartition(username, containersPath):
    execShellCommand("mkdir -p " + containersPath)
    filename = containersPath + username + ".container"
    execShellCommand("fallocate -l 200MB " + filename)
    execShellCommand("chmod 600 " + filename)
    return filename

def generatePassword():
    return str(random.getrandbits(getPasswordSize()))

def savePassword(username, password, keysPath):
    execShellCommand("mkdir -p " + keysPath)
    filename = keysPath + username + ".key"
    with open(filename, 'w') as data_file:
        data_file.write(password)
    execShellCommand("chmod 600 " + filename)
    return filename

def getPasswordSize():
    return 128

def readPasswordOfUser(userConfig):
    passwordPath = getPasswordPathInUserConfiguration(userConfig)
    with open(passwordPath, 'r') as data_file:
        return data_file.read(getPasswordSize())

def openSession(username, configurationPath = "/etc/encrypted_containers.conf.json", containersPath = "/containers/", keysPath = "/keys/"):
    configuration = getConfiguration(configurationPath)
    userConfig = getUserConfiguration(configuration, username)
    partition = None
    if userConfig == None:
        partition = getNewPartition(username, containersPath)
        password = generatePassword()
        passwordPath = savePassword(username, password, keysPath)
        formatLuks(partition, username, password)
        openLuks(partition, username, password)
        createContainer(partition, username)
        addUserConfiguration(configuration, username, partition, passwordPath)
        saveConfiguration(configuration, configurationPath)
    else:
        partition = getPartitionInUserConfiguration(userConfig)
        password = readPasswordOfUser(userConfig)
        openLuks(partition, username, password)
    openContainer(partition, username)
    print("opened")

def closeContainer(username):
    execShellCommand("umount /home/" + username + "/secret")
    execShellCommand("cryptsetup luksClose " + username)

def closeSession(username):
    closeContainer(username)
    print("Closed")

if 'PAM_TYPE' in os.environ and os.environ['PAM_TYPE'] == "open_session":
    openSession(os.environ['PAM_USER'])
elif 'PAM_TYPE' in os.environ and os.environ['PAM_TYPE' == "close_session"]:
    closeSession(os.environ['PAM_USER'])
else:
    openSession(os.environ['PAM_USER'], "./configuration.test.json", "./", "./")
