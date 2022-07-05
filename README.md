# ANS v1.0 registry smart contracts

Smart contract and logic signature code for Algorand Name Service v1.0

## Run unit tests on testnet
Add PureStake API key to `unit-tests/mysecrets.py`
```python
# unit-tests/mysecrets.py
MY_PURESTAKE_TOKEN="<y0uRtOK3nHere>"

FUNDING_ACCOUNT_MNEMONIC="<enter account mnemonic that canbe used tofund accounts>"
```

Add Algos to funding account from testnet [faucet](https://bank.testnet.algorand.network/)

Change directory into unit-tests and run python scripts:
```bash
cd unit-tests
python3 TestDotAlgoNameRegistry.py
```
