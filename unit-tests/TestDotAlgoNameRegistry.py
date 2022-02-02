import unittest, time
import json

import ans_helper as anshelper

class TestDotAlgoNameRegistry(unittest.TestCase):

    def setUp(self) -> None:
        self.algod_client = anshelper.SetupClient("purestake")
        self.funding_addr, self.funding_acct_mnemonic = anshelper.GetFundingAccount(self.algod_client)
        self.algod_indexer = anshelper.SetupIndexer("purestake")
        return super().setUp()

class DeployNameRegistry(TestDotAlgoNameRegistry):
    def test_deploynameregistry(self):
        new_acct_addr, new_acct_mnemonic = anshelper.GenerateAccount()

        print("Generated new account: "+new_acct_addr)

        anshelper.FundNewAccount(self.algod_client, new_acct_addr, 3401000, self.funding_acct_mnemonic)    

        print("Funded 3401000 to new account for the purpose of deploying registry")
        print("Funding account: "+self.funding_addr)

        # Set App index
        app_index= anshelper.DeployANS(self.algod_client,new_acct_mnemonic)

        print("Deployed .algo registry to APP_ID: "+str(app_index))
        time.sleep(5)
        response=self.algod_indexer.applications(app_index)
        self.assertEqual(app_index, response["application"]["id"])
        self.assertEqual(new_acct_addr,response["application"]["params"]["creator"])

    def tearDown(self) -> None:
        # TODO: clear all variables?
        return super().tearDown()

if __name__ == '__main__':
    unittest.main()