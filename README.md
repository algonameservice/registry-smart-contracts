# ANS v1.0 registry smart contracts

Smart contract and logic signature code for Algorand Name Service v1.0

## Run unit tests
Add PureStake API key to `unit-tests/mysecrets.py`
```python
# unit-tests/mysecrets.py
MY_PURESTAKE_TOKEN="<your-token>"
```

Change directory into unit-tests and run python scripts:
```bash
cd unit-tests
python3 TestDotAlgoNameRegistry.py
```
**Note:** `KLRZGUWF5WDUWZXSGCWA723FLZXMQ4GIPXD2UYJ6C74X3N3NES4QH5XIF4` is the funding address used to generate accounts and test registry operations
