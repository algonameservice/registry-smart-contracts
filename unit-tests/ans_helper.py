'''
Copyright (c) 2022 Algorand Name Service DAO LLC

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

from algosdk import mnemonic, account, encoding
from algosdk.future import transaction
from algosdk.future.transaction import LogicSig, LogicSigTransaction, LogicSigAccount
from algosdk.v2client import algod, indexer
from algosdk import logic
import json
from pyteal import *

import sys
sys.path.append('../')

from contracts.dot_algo_registry import approval_program, clear_state_program
from contracts.dot_algo_name_record import ValidateRecord
import base64
import datetime,time
import mysecrets


def SetupClient(network):

    if(network=="sandbox"):
        # Local sandbox node 
        algod_address = "http://localhost:4001"
        algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    elif(network=="purestake"):
        # Purestake conn
        algod_address = "https://testnet-algorand.api.purestake.io/ps2"
        algod_token = mysecrets.MY_PURESTAKE_TOKEN
        headers = {
            "X-API-Key": mysecrets.MY_PURESTAKE_TOKEN
        }
    
    else:
        raise ValueError

    algod_client=algod.AlgodClient(algod_token, algod_address, headers=headers)
    return algod_client

def SetupIndexer(network):
    if(network=="purestake"):
        algod_address = "https://testnet-algorand.api.purestake.io/idx2"
        headers = {
            'X-API-key' : mysecrets.MY_PURESTAKE_TOKEN,
        }
        algod_indexer=indexer.IndexerClient("", algod_address, headers)
    
    return algod_indexer

def GetFundingAccount(algod_client):

    passphrase = mysecrets.FUNDING_ACCOUNT_MNEMONIC

    private_key = mnemonic.to_private_key(passphrase)
    sender = account.address_from_private_key(private_key)

    account_info = algod_client.account_info(sender)

    return sender, passphrase

def GenerateAccount():
    new_private_key, new_address = account.generate_account()
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

def DeployDotAlgoReg(algod_client, contract_owner_mnemonic):

    private_key=mnemonic.to_private_key(contract_owner_mnemonic)
    sender=account.address_from_private_key(private_key)

    # Setup Schema
    local_ints = 4 
    local_bytes = 12 
    global_ints = 32 
    global_bytes = 32 
    global_schema = transaction.StateSchema(global_ints, global_bytes)
    local_schema = transaction.StateSchema(local_ints, local_bytes)

    on_complete = transaction.OnComplete.NoOpOC.real

    compileTeal(approval_program(sender), Mode.Application,version=5)
    compileTeal(clear_state_program(), Mode.Application,version=5)

    ans_approval_program = compile_program(algod_client, import_teal_source_code_as_binary('dot_algo_registry_approval.teal'))
    ans_clear_state_program = compile_program(algod_client, import_teal_source_code_as_binary('dot_algo_registry_clear_state.teal'))

    txn = transaction.ApplicationCreateTxn(sender, algod_client.suggested_params(), on_complete, ans_approval_program, ans_clear_state_program, global_schema, local_schema)

    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    algod_client.send_transactions([signed_txn])

    # await confirmation
    wait_for_confirmation(algod_client, tx_id)

    # display results
    transaction_response = algod_client.pending_transaction_info(tx_id)
    app_id = transaction_response['application-index']
    print("Deployed new Dot Algo Registry with App-id: ",app_id)

    return app_id

def prep_name_record_logic_sig(algod_client, name, reg_app_id):
    reg_escrow_acct = logic.get_application_address(reg_app_id)
    logic_sig_teal = compileTeal(ValidateRecord(name,reg_app_id,reg_escrow_acct), Mode.Signature, version=4)
    validate_name_record_program = compile_program(algod_client, str.encode(logic_sig_teal))
    lsig = LogicSig(validate_name_record_program)

    return lsig

def get_name_price(name):
    #TODO: Find out max length of name, is 1 char = 1 byte?
    assert(len(name)>=3 and len(name)<=64)
    # Returns name price in ALGOs
    if(len(name)==3):
        return 150000000
    elif(len(name)==4):
        return 50000000
    else:
        return 5000000

def prep_name_reg_gtxn(sender, name, validity, reg_app_id, algod_client):
    
    # Prepare group txn array
    Grp_txns_unsign = []

    # 1. PaymentTxn to Smart Contract
    reg_escrow_acct = logic.get_application_address(reg_app_id)
    pmnt_txn_unsign = transaction.PaymentTxn(sender, algod_client.suggested_params(), reg_escrow_acct, get_name_price(name), None)
    Grp_txns_unsign.append(pmnt_txn_unsign)


    # 2. Funding lsig
    lsig = prep_name_record_logic_sig(algod_client, name, reg_app_id)
    # Min amount necessary: 915000
    fund_lsig_txn_unsign = transaction.PaymentTxn(sender, algod_client.suggested_params(), lsig.address(), 915000, None, None)
    Grp_txns_unsign.append(fund_lsig_txn_unsign)

    # 3. Optin to registry
    optin_txn_unsign = transaction.ApplicationOptInTxn(lsig.address(), algod_client.suggested_params(), reg_app_id)
    Grp_txns_unsign.append(optin_txn_unsign)

    # 4. Write name and owner's address in local storage
    txn_args = [
        "register_name".encode("utf-8"),
        name.encode("utf-8"),
        validity.to_bytes(8, "big")
    ]
    store_owners_add_txn_unsign = transaction.ApplicationNoOpTxn(sender, algod_client.suggested_params(), reg_app_id, txn_args, [lsig.address()])
    Grp_txns_unsign.append(store_owners_add_txn_unsign)

    gid = transaction.calculate_group_id(Grp_txns_unsign)
    for i in range(0,4):
        Grp_txns_unsign[i].group = gid

    return Grp_txns_unsign, lsig

# Sign and send transactions
def sign_name_reg_gtxn(sender_add, sender_private_key, Grp_txns_unsign, lsig, algod_client):
    Grp_txns_signed = [Grp_txns_unsign[0].sign(sender_private_key)]
    Grp_txns_signed.append(Grp_txns_unsign[1].sign(sender_private_key))
    Grp_txns_signed.append(LogicSigTransaction(Grp_txns_unsign[2],lsig))
    assert Grp_txns_signed[2].verify()
    Grp_txns_signed.append(Grp_txns_unsign[3].sign(sender_private_key))

    algod_client.send_transactions(Grp_txns_signed)

    wait_for_confirmation(algod_client,Grp_txns_signed[3].transaction.get_txid())

def link_socials(domainname, platform_name, profile, sender, sender_private_key, reg_app_id, algod_client):
    
    txn_args = [
        "update_name".encode("utf-8"),
        platform_name.encode("utf-8"),
        profile.encode("utf-8"),
    ]
    reg_escrow_acct = logic.get_application_address(reg_app_id)
    lsig = prep_name_record_logic_sig(algod_client, domainname, reg_app_id)
    link_social_txn_unsign = transaction.ApplicationNoOpTxn(sender, algod_client.suggested_params(), reg_app_id, txn_args, [lsig.address()])
    txn_signed_link_social = link_social_txn_unsign.sign(sender_private_key)
    txid = txn_signed_link_social.get_txid()
    algod_client.send_transaction(txn_signed_link_social)
    wait_for_confirmation(algod_client,txid)

def update_rslvr_acc_txn(domainname, sender, sender_private_key, resolver_addr, reg_app_id, algod_client):

    txn_args = [
        "update_resolver_account".encode("utf-8")
    ]
    lsig = prep_name_record_logic_sig(algod_client, domainname, reg_app_id)
    txn_update_rslvr_acc_unsign = transaction.ApplicationNoOpTxn(sender, algod_client.suggested_params(), reg_app_id, txn_args, [lsig.address(),resolver_addr])
    txn_update_rslvr_signd = txn_update_rslvr_acc_unsign.sign(sender_private_key)
    txid = txn_update_rslvr_signd.get_txid()
    algod_client.send_transaction(txn_update_rslvr_signd)
    wait_for_confirmation(algod_client, txid)    

def init_name_tnsfr_txn(domainname, sender, sender_private_key, tnsfr_price, recipient_addr, reg_app_id, algod_client):

    txn_args = [
        "initiate_transfer".encode("utf-8"),
        tnsfr_price.to_bytes(8, "big")
    ]
    lsig = prep_name_record_logic_sig(algod_client, domainname, reg_app_id)
    txn_init_name_tnsfr_unsign = transaction.ApplicationNoOpTxn(sender, algod_client.suggested_params(), reg_app_id, txn_args, [lsig.address(),recipient_addr])
    txn_init_name_tnsfr_signd = txn_init_name_tnsfr_unsign.sign(sender_private_key)
    txid = txn_init_name_tnsfr_signd.get_txid()
    algod_client.send_transaction(txn_init_name_tnsfr_signd)
    wait_for_confirmation(algod_client, txid)

def withdraw_name_tnsfr_txn(domainname, sender, sender_private_key, reg_app_id, algod_client):

    txn_args = [
        "withdraw_transfer".encode("utf-8")
    ]
    lsig = prep_name_record_logic_sig(algod_client, domainname, reg_app_id)
    txn_withdraw_name_tnsfr_unsign = transaction.ApplicationNoOpTxn(sender, algod_client.suggested_params(), reg_app_id, txn_args, [lsig.address()])
    txn_withdraw_name_tnsfr_signd = txn_withdraw_name_tnsfr_unsign.sign(sender_private_key)
    txid = txn_withdraw_name_tnsfr_signd.get_txid()
    algod_client.send_transaction(txn_withdraw_name_tnsfr_signd)
    wait_for_confirmation(algod_client, txid)    

def prep_cmplte_name_tnsfr_gtxn(domainname, sender, tnsfr_price, recipient_addr, reg_app_id, algod_client):

    # TODO: Assert if sender is authorized to complete
    # Prepare group txn array
    Grp_txns_unsign = []

    # 1. Payment for name transfer 
    pmnt_txn_unsign = transaction.PaymentTxn(sender, algod_client.suggested_params(), recipient_addr, tnsfr_price, None)
    Grp_txns_unsign.append(pmnt_txn_unsign)

    # 2. Transfer fee payment to registry 
    reg_escrow_acct = logic.get_application_address(reg_app_id)
    tnsfr_fee_pmnt_txn_unsign = transaction.PaymentTxn(sender, algod_client.suggested_params(), reg_escrow_acct, 2000000, None)
    Grp_txns_unsign.append(tnsfr_fee_pmnt_txn_unsign)

    # 3. 
    txn_args = [
        "accept_transfer".encode("utf-8"),
    ]
    lsig = prep_name_record_logic_sig(algod_client, domainname, reg_app_id)
    txn_accpt_name_tnsfr_unsign = transaction.ApplicationNoOpTxn(sender, algod_client.suggested_params(), reg_app_id, txn_args, [lsig.address()])
    Grp_txns_unsign.append(txn_accpt_name_tnsfr_unsign)

    gid = transaction.calculate_group_id(Grp_txns_unsign)
    for i in range(3):
        Grp_txns_unsign[i].group = gid

    return Grp_txns_unsign

def sign_cmplte_name_tnsfr_gtxn(grp_txns_unsign, sender_private_key,algod_client):
    Grp_txns_signd = [grp_txns_unsign[0].sign(sender_private_key)] 
    Grp_txns_signd.append(grp_txns_unsign[1].sign(sender_private_key))
    Grp_txns_signd.append(grp_txns_unsign[2].sign(sender_private_key))
    algod_client.send_transactions(Grp_txns_signd)
    wait_for_confirmation(algod_client,Grp_txns_signd[2].transaction.get_txid())

def set_default_acc_txn(domainname, sender, sender_private_key, reg_app_id, algod_client):

    txn_args = [
        "set_default_account".encode("utf-8")
    ]

    lsig = prep_name_record_logic_sig(algod_client, domainname, reg_app_id)
    txn_set_default_acc_unsign = transaction.ApplicationNoOpTxn(sender, algod_client.suggested_params(), reg_app_id, txn_args, [lsig.address()])
    txn_set_default_acc_signd = txn_set_default_acc_unsign.sign(sender_private_key)
    txid = txn_set_default_acc_signd.get_txid()
    algod_client.send_transaction(txn_set_default_acc_signd)
    wait_for_confirmation(algod_client, txid)   

  

def get_socials(algod_client, name, platform_name, reg_app_id):
    list_platforms = ["discord","github","twitter","reddit","telegram","youtube"]
    assert(platform_name in list_platforms)

    algod_indexer = SetupIndexer("purestake")
    reg_escrow_acct = logic.get_application_address(reg_app_id)
    # TODO: Need proper error handling, this fails keynotfound
    for apps_local_data in algod_indexer.account_info(address=prep_name_record_logic_sig(algod_client, name, reg_app_id).address())['account']['apps-local-state']:
        profile_name = None
        expiry = None
        if(apps_local_data['id']==reg_app_id and not apps_local_data['deleted']):
            for key_value in apps_local_data['key-value']:
                if(base64.b64decode(key_value['key']).decode()=="expiry"):
                    expiry = key_value['value']['uint']
                elif(base64.b64decode(key_value['key']).decode()==platform_name):
                    profile_name = base64.b64decode(key_value['value']['bytes']).decode()
        if(profile_name!=None and expiry!=None and expiry>int(time.time())):
            return profile_name
        else:
            return None

def resolve_name(algod_client, name, reg_app_id):
    # TODO: Make sure there are no edge cases
    algod_indexer = SetupIndexer("purestake")
    reg_escrow_acct = logic.get_application_address(reg_app_id)
    for apps_local_data in algod_indexer.account_info(address=prep_name_record_logic_sig(algod_client,name, reg_app_id).address())['account']['apps-local-state']:
        owner = None
        expiry = None
        if(apps_local_data['id']==reg_app_id and not apps_local_data['deleted']):
            for key_value in apps_local_data['key-value']:
                if(base64.b64decode(key_value['key']).decode()=="expiry"):
                    expiry = key_value['value']['uint']
                elif(base64.b64decode(key_value['key']).decode()=="owner"):
                    owner = encoding.encode_address(base64.b64decode(key_value['value']['bytes']))
        if(owner!=None and expiry!=None and expiry>int(time.time())):
            return owner
        else:
            return None

def get_name_expiry(algod_client, name, reg_app_id):
    # TODO: Make sure there are no edge cases
    algod_indexer = SetupIndexer("purestake")
    reg_escrow_acct = logic.get_application_address(reg_app_id)
    for apps_local_data in algod_indexer.account_info(address=prep_name_record_logic_sig(algod_client,name, reg_app_id).address())['account']['apps-local-state']:
        if(apps_local_data['id']==reg_app_id and not apps_local_data['deleted']):
            for key_value in apps_local_data['key-value']:
                if(base64.b64decode(key_value['key']).decode()=="expiry"):
                    expiry = key_value['value']['uint']
                    return expiry
        return None


def renew_name(algod_client,domainname,no_years,reg_app_id,sender_private_key):
    # Prepare group txn array
    Grp_txns_unsign = []

    # 1. PaymentTxn to Smart Contract
    reg_escrow_acct = logic.get_application_address(reg_app_id)
    sender = account.address_from_private_key(sender_private_key)
    pmnt_txn_unsign = transaction.PaymentTxn(sender, algod_client.suggested_params(), reg_escrow_acct, get_name_price(domainname)*no_years, None)
    Grp_txns_unsign.append(pmnt_txn_unsign)


    txn_args = [
        "renew_name".encode("utf-8"),
        no_years.to_bytes(8, "big")
    ]
    lsig = prep_name_record_logic_sig(algod_client,domainname, reg_app_id)
    renewal_txn_unsign = transaction.ApplicationNoOpTxn(sender, algod_client.suggested_params(), reg_app_id, txn_args, [lsig.address()])
    Grp_txns_unsign.append(renewal_txn_unsign)

    transaction.assign_group_id(Grp_txns_unsign)

    Grp_txns_signed = [ txn.sign(sender_private_key) for txn in Grp_txns_unsign]

    txid = Grp_txns_signed[1].get_txid()

    algod_client.send_transactions(Grp_txns_signed)
    wait_for_confirmation(algod_client,txid)

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
    print("Transaction {} confirmed in round {}.".format(txid, txinfo.get('confirmed-round')))
    return txinfo

if __name__ == "__main__":
    main()
