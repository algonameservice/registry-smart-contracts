from algosdk import mnemonic, account
from algosdk.future import transaction
from algosdk.v2client import algod, indexer
import json
from pyteal import *
from dot_algo_registry import approval_program, clear_state_program
import base64
import datetime


def SetupClient(network):

    if(network=="sandbox"):
        # Local sandbox node 
        algod_address = "http://localhost:4001"
        algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    elif(network=="purestake"):
        # Purestake conn
        algod_address = "https://testnet-algorand.api.purestake.io/ps2"
        algod_token = "iG4m46pAcU5ws8WYhgYPu1rywUbfYT2DaAfSs9Tv"
        headers = {
        "X-API-Key": algod_token,
        }
    
    else:
        raise ValueError

    algod_client=algod.AlgodClient(algod_token, algod_address, headers=headers)
    return algod_client

def SetupIndexer(network):
    if(network=="purestake"):
        algod_address = "https://testnet-algorand.api.purestake.io/idx2"
        headers = {
            'X-API-key' : 'iG4m46pAcU5ws8WYhgYPu1rywUbfYT2DaAfSs9Tv',
        }
        algod_indexer=indexer.IndexerClient("", algod_address, headers)
    
    return algod_indexer

def GetFundingAccount(algod_client):

    # address: KLRZGUWF5WDUWZXSGCWA723FLZXMQ4GIPXD2UYJ6C74X3N3NES4QH5XIF4
    passphrase= "crumble inquiry mixed teach february usage nerve nose brain angry broccoli attend cram empower immense chest safe field cup head badge strategy clip absent dice"

    private_key = mnemonic.to_private_key(passphrase)
    sender = account.address_from_private_key(private_key)
    #print("Sender address: {}".format(sender))

    account_info = algod_client.account_info(sender)
    #print("Account balance: {} microAlgos".format(account_info.get('amount')))

    return sender, passphrase

def GenerateAccount():
    new_private_key, new_address = account.generate_account()
    #print("New address: {}".format(new_address))
    #print("Passphrase: {}".format(mnemonic.from_private_key(new_private_key)))
    return new_address, mnemonic.from_private_key(new_private_key)

def FundNewAccount(algod_client, receiver, amount, funding_acct_mnemonic):

    sender_private_key=mnemonic.to_private_key(funding_acct_mnemonic)
    sender=account.address_from_private_key(sender_private_key)

    unsigned_txn = transaction.PaymentTxn(sender, algod_client.suggested_params(), receiver,amount, None)
    signed_txn = unsigned_txn.sign(sender_private_key)

    #submit transaction
    txid = algod_client.send_transaction(signed_txn)
    print("Successfully sent transaction with txID: {}".format(txid))

    # wait for confirmation 
    try:
        confirmed_txn = wait_for_confirmation(algod_client,txid)  
    except Exception as err:
        print(err)
        return

    #print("Transaction information: {}".format(
    #    json.dumps(confirmed_txn, indent=4)))

def DeployANS(algod_client, contract_owner_mnemonic):

    private_key=mnemonic.to_private_key(contract_owner_mnemonic)
    sender=account.address_from_private_key(private_key)

    # Setup Schema
    local_ints = 0 
    local_bytes = 0 
    global_ints = 0 
    global_bytes = 64 
    global_schema = transaction.StateSchema(global_ints, global_bytes)
    local_schema = transaction.StateSchema(local_ints, local_bytes)

    on_complete = transaction.OnComplete.NoOpOC.real

    compileTeal(approval_program(), Mode.Application,version=5)
    compileTeal(clear_state_program(), Mode.Application,version=5)

    ans_approval_program = compile_program(algod_client, import_teal_source_code_as_binary('dot_algo_registry_approval.teal'))
    ans_clear_state_program = compile_program(algod_client, import_teal_source_code_as_binary('dot_algo_registry_clear_state.teal'))

    txn = transaction.ApplicationCreateTxn(sender, algod_client.suggested_params(), on_complete, ans_approval_program, ans_clear_state_program, global_schema, local_schema)

    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    print(tx_id)

    # send transaction
    algod_client.send_transactions([signed_txn])

    # await confirmation
    wait_for_confirmation(algod_client, tx_id)

    # display results
    transaction_response = algod_client.pending_transaction_info(tx_id)
    app_id = transaction_response['application-index']
    print("Created new app-id: ",app_id)

    return app_id


# helper function to compile program source
def compile_program(algod_client, source_code) :
    compile_response = algod_client.compile(source_code.decode('utf-8'))
    return base64.b64decode(compile_response['result'])

def import_teal_source_code_as_binary(file_name):
    with open(file_name, 'r') as f:
        data = f.read()
        return str.encode(data)

# helper function that waits for a given txid to be confirmed by the network
def wait_for_confirmation(algod_client,txid) :
    last_round = algod_client.status().get('last-round')
    txinfo = algod_client.pending_transaction_info(txid)
    while not (txinfo.get('confirmed-round') and txinfo.get('confirmed-round') > 0):
        print("Waiting for txn confirmation...")
        last_round += 1
        algod_client.status_after_block(last_round)
        txinfo = algod_client.pending_transaction_info(txid)
    #print("Transaction {} confirmed in round {}.".format(txid, txinfo.get('confirmed-round')))
    return txinfo

def opt_in_app(private_key, index):
    # declare sender
    sender = account.address_from_private_key(private_key)
    print("OptIn from account: ", sender)

    # create unsigned transaction
    txn = transaction.ApplicationOptInTxn(sender, algod_client.suggested_params(), index)

    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    algod_client.send_transactions([signed_txn])

    # await confirmation
    wait_for_confirmation(algod_client,tx_id)

    # display results
    transaction_response = algod_client.pending_transaction_info(tx_id)
    print("OptIn to app-id:", transaction_response["txn"]["txn"]["apid"])


def RegisterName(algod_client, app_index, name, account_mnemonic):

    private_key=mnemonic.to_private_key(account_mnemonic)
    sender=account.address_from_private_key(private_key)

    on_complete = transaction.OnComplete.NoOpOC.real

    #opt_in_app(algod_client,private_key,app_index)

    # Set Application args
    register_name=b"register_name"
    #name=b"sanjay"


    # create unsigned transaction
    txn = transaction.ApplicationNoOpTxn(sender, algod_client.suggested_params(), app_index, app_args=[register_name,name])

    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    algod_client.send_transactions([signed_txn])

    # await confirmation
    wait_for_confirmation(algod_client,tx_id)

    # display results
    transaction_response = algod_client.pending_transaction_info(tx_id)
    print("Called app-id: ",transaction_response['txn']['txn']['apid'])
    if "global-state-delta" in transaction_response :
        print("Global State updated :\n",transaction_response['global-state-delta'])
    if "local-state-delta" in transaction_response :
        print("Local State updated :\n",transaction_response['local-state-delta'])

if __name__ == "__main__":
    main()
