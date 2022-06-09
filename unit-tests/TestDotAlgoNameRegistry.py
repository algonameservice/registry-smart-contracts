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

import unittest, time
from algosdk import mnemonic
import json, random, string

import ans_helper as anshelper

unittest.TestLoader.sortTestMethodsUsing = None

class TestDotAlgoNameRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.algod_client = anshelper.SetupClient("purestake")
        cls.funding_addr, cls.funding_acct_mnemonic = anshelper.GetFundingAccount(cls.algod_client)
        cls.algod_indexer = anshelper.SetupIndexer("purestake")

        cls.new_acct_addr, cls.new_acct_mnemonic = anshelper.GenerateAccount()

        print("Generated new account: "+cls.new_acct_addr)
 
        cls.name = ''.join(random.choice(string.ascii_lowercase) for i in range(6))

        cls.app_index = 0

#class DeployNameRegistry(TestDotAlgoNameRegistry):
    
    def test_a_deploynameregistry(self):
        new_acct_addr, new_acct_mnemonic = anshelper.GenerateAccount()

        print("Generated new account: "+new_acct_addr)
        print("Account mnemonic: "+new_acct_mnemonic)
        anshelper.FundNewAccount(TestDotAlgoNameRegistry.algod_client, new_acct_addr, 3401000, TestDotAlgoNameRegistry.funding_acct_mnemonic)    

        print("Funded 3401000 to new account for the purpose of deploying registry")
        print("Funding account: "+TestDotAlgoNameRegistry.funding_addr)

        # Set App index
        TestDotAlgoNameRegistry.app_index = anshelper.DeployDotAlgoReg(TestDotAlgoNameRegistry.algod_client,new_acct_mnemonic)

        print("Deployed .algo registry to APP_ID: "+str(TestDotAlgoNameRegistry.app_index))
        time.sleep(5)
        response=TestDotAlgoNameRegistry.algod_indexer.applications(TestDotAlgoNameRegistry.app_index)
        self.assertEqual(TestDotAlgoNameRegistry.app_index, response["application"]["id"])
        self.assertEqual(new_acct_addr,response["application"]["params"]["creator"])

#class RegisterDotAlgoName(TestDotAlgoNameRegistry):
        
    def test_b_register5letterdotalgoname(self):

        anshelper.FundNewAccount(TestDotAlgoNameRegistry.algod_client, TestDotAlgoNameRegistry.new_acct_addr, 12000000, TestDotAlgoNameRegistry.funding_acct_mnemonic)    

        print("Funded 12000000 to new account for the purpose of registering name")
        print("Funding account: "+TestDotAlgoNameRegistry.funding_addr)

        print("DEBUG: Registry deployed to "+str(TestDotAlgoNameRegistry.app_index))

        print("Name: "+TestDotAlgoNameRegistry.name+" to be owned by: "+ TestDotAlgoNameRegistry.new_acct_addr)
        gtx_unsign_regname, lsig =  anshelper.prep_name_reg_gtxn(TestDotAlgoNameRegistry.new_acct_addr, TestDotAlgoNameRegistry.name , 1, TestDotAlgoNameRegistry.app_index, TestDotAlgoNameRegistry.algod_client)
        anshelper.sign_name_reg_gtxn( TestDotAlgoNameRegistry.new_acct_addr, mnemonic.to_private_key(TestDotAlgoNameRegistry.new_acct_mnemonic), gtx_unsign_regname, lsig, TestDotAlgoNameRegistry.algod_client)
        time.sleep(10)
        self.assertEqual(anshelper.resolve_name(TestDotAlgoNameRegistry.algod_client, TestDotAlgoNameRegistry.name, TestDotAlgoNameRegistry.app_index), TestDotAlgoNameRegistry.new_acct_addr)
        print("Name: "+TestDotAlgoNameRegistry.name+" is owned by: "+ anshelper.resolve_name(TestDotAlgoNameRegistry.algod_client, TestDotAlgoNameRegistry.name, TestDotAlgoNameRegistry.app_index))

    def test_c_renewname(self):
        # TODO: Find best way to split this method
        name_expiry = anshelper.get_name_expiry(TestDotAlgoNameRegistry.algod_client,TestDotAlgoNameRegistry.name,TestDotAlgoNameRegistry.app_index)
        account_info = TestDotAlgoNameRegistry.algod_client.account_info(TestDotAlgoNameRegistry.new_acct_addr)
        print("Account balance: {} microAlgos".format(account_info.get('amount')))
        anshelper.renew_name(TestDotAlgoNameRegistry.algod_client,TestDotAlgoNameRegistry.name,1,TestDotAlgoNameRegistry.app_index,mnemonic.to_private_key(TestDotAlgoNameRegistry.new_acct_mnemonic))
        time.sleep(5)
        self.assertGreater(anshelper.get_name_expiry(TestDotAlgoNameRegistry.algod_client,TestDotAlgoNameRegistry.name,TestDotAlgoNameRegistry.app_index),name_expiry)

    def test_d_linksocials_twitter(self):
        # TODO: Find best way to split this method
        profile = ''.join(random.choice(string.ascii_lowercase) for i in range(5))
        anshelper.link_socials(TestDotAlgoNameRegistry.name,"twitter",profile,TestDotAlgoNameRegistry.new_acct_addr,mnemonic.to_private_key(TestDotAlgoNameRegistry.new_acct_mnemonic),TestDotAlgoNameRegistry.app_index,TestDotAlgoNameRegistry.algod_client)
        time.sleep(5)
        self.assertEqual(anshelper.get_socials(TestDotAlgoNameRegistry.algod_client, TestDotAlgoNameRegistry.name,"twitter",TestDotAlgoNameRegistry.app_index),profile)

        #TODO: Repeat tests for other socials

    def test_e_set_account_prop(self):

        print("Test 6: Set Resolver Property")
        
        update_rslvr_txn = anshelper.update_rslvr_acc_txn(TestDotAlgoNameRegistry.name, TestDotAlgoNameRegistry.new_acct_addr, mnemonic.to_private_key(TestDotAlgoNameRegistry.new_acct_mnemonic), TestDotAlgoNameRegistry.funding_addr,TestDotAlgoNameRegistry.app_index,TestDotAlgoNameRegistry.algod_client)

    
    def test_e_setdefaultaccount(self):

        print("Test 7: Set Default Account")
        set_default_account_txn = anshelper.set_default_acc_txn(TestDotAlgoNameRegistry.name, TestDotAlgoNameRegistry.new_acct_addr, mnemonic.to_private_key(TestDotAlgoNameRegistry.new_acct_mnemonic), TestDotAlgoNameRegistry.app_index,TestDotAlgoNameRegistry.algod_client)

    def test_e_transfername(self):

        print("Test 8: Transfer Name")
        tnsfr_price = 4000000
        init_name_tnsfr_txn = anshelper.init_name_tnsfr_txn(TestDotAlgoNameRegistry.name, TestDotAlgoNameRegistry.new_acct_addr, mnemonic.to_private_key(TestDotAlgoNameRegistry.new_acct_mnemonic), tnsfr_price, TestDotAlgoNameRegistry.funding_addr,TestDotAlgoNameRegistry.app_index,TestDotAlgoNameRegistry.algod_client)

        withdraw_name_tnsfr_txn = anshelper.withdraw_name_tnsfr_txn(TestDotAlgoNameRegistry.name, TestDotAlgoNameRegistry.new_acct_addr, mnemonic.to_private_key(TestDotAlgoNameRegistry.new_acct_mnemonic), TestDotAlgoNameRegistry.app_index,TestDotAlgoNameRegistry.algod_client)

        init_name_tnsfr_txn = anshelper.init_name_tnsfr_txn(TestDotAlgoNameRegistry.name, TestDotAlgoNameRegistry.new_acct_addr, mnemonic.to_private_key(TestDotAlgoNameRegistry.new_acct_mnemonic), tnsfr_price, TestDotAlgoNameRegistry.funding_addr,TestDotAlgoNameRegistry.app_index,TestDotAlgoNameRegistry.algod_client)
        #TODO: Send accept name transfer txn
        name_tnsfr_gtxn = anshelper.prep_cmplte_name_tnsfr_gtxn(TestDotAlgoNameRegistry.name, TestDotAlgoNameRegistry.funding_addr, tnsfr_price, TestDotAlgoNameRegistry.new_acct_addr, TestDotAlgoNameRegistry.app_index, TestDotAlgoNameRegistry.algod_client)

        anshelper.sign_cmplte_name_tnsfr_gtxn(name_tnsfr_gtxn, mnemonic.to_private_key(TestDotAlgoNameRegistry.funding_acct_mnemonic),TestDotAlgoNameRegistry.algod_client)

    


# TODO: See where tearDown goes, class or outside
def tearDownClass(self) -> None:
    # TODO: clear all variables?
    return super().tearDown()

if __name__ == '__main__':
    unittest.main()
