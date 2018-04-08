##
# Title: Buffer app to complete background processes without hindering presentation
# layer - i.e. alexa or web. How? by checking if the 1st add patient transaction
# has been mined successfully on the ethereum network then processing the 2nd add sick
# transaction.
# Version: v00_01
# Author: Nzwisisa Chidembo <nzwisisa@gmail.com>
##

import boto3
import requests
from web3 import Web3, HTTPProvider, Account

dynamodb = boto3.resource('dynamodb')
sms = boto3.client('sns')

# ---------------------Settings for the buffer app------------------------ #
settings = {
    "httpProvider": "",
    "contractAddress": "",
    "adminWalletAddress": "",
    "adminWalletPrivateKey": "",
    "chainId": 3,
    "gas": 2000000,
    "gasPrice": 10000000000,
    "bufferTableName": "",
    "ethAPIEndPoint": ""
}

def scanItemsNoFilter(TableName):
	table = dynamodb.Table(TableName)
	response = table.scan()
	return response['Items']

def deleteBatch(TableName, Items):
	table = dynamodb.Table(TableName)
	with table.batch_writer() as batch:
		for item in Items:
			batch.delete_item(
				Key = item
			)

def deleteItem(TableName, Id):
    table = dynamodb.Table(TableName)
    table.delete_item(
        Key = {
            'add_patient_tx_hash': Id
        }
    )

def isAddPatientComplete(data):
    contract_abi = ''

    #End the uri to your contract ABI file below
    with open('xxxxxxxxxxxxxxx','r') as f:
        contract_abi = eval(f.read())

    infura_provider = HTTPProvider(settings['httpProvider'])
    web3 = Web3(infura_provider)

    address = settings['contractAddress']

    myContract = web3.eth.contract(
        address = address,
        abi = contract_abi
    )

    res = web3.eth.getTransactionReceipt(data['add_patient_tx_hash'])

    if res['status'] == None:
        return False
    else:
        return bool(res['status'])

def addNoteToBlockchain(data):

    req = {
        "request": {
            "type": "AddNote",
            "data": {
                "practiceNo": int(data['practiceNo']),
                "patientId": int(data['patientId']),
                "sickDays": int(data['sickDays']),
                "illnessDescription": data['illnessDescription']
            }
        }
    }

    url = settings['ethAPIEndPoint']

    #Enter your API gateway api-key below
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': 'xxxxxxxxxxxxxxxxxxxxxx'
    }

    res = requests.post(url,json=req,headers=headers).json()

    return res['response']['data']['transactionHash']

def sendSMSNotification(data):
    number = ''
    if len(data['mobileNo']) == 9:
        number = '+27' + data['mobileNo']
    elif len(data['mobileNo']) == 10:
        number = '+27' + data['mobileNo'][1:]

    #Replace the xxxxxxxxxxxxxx with your url link for your S3
    message = "Hi. Below is a link to your sick note: http://xxxxxxxxxxxxxxxxxx.amazonaws.com/sicknote/" + str(data['patientId'])

    sms.publish(PhoneNumber=number, Message=message)

def updateBufferRecords(data):
    deleteItem(
        TableName = settings['bufferTableName'],
        Id = data
    )

def main():
    deleteBufferRecords = []
    for i in scanItemsNoFilter(settings['bufferTableName']):
        if bool(int(i['isVerified'])):
            pass
        else:
            if isAddPatientComplete(i):
                addNoteToBlockchain(i)
                sendSMSNotification(i)
                updateBufferRecords(i['add_patient_tx_hash'])
main()
