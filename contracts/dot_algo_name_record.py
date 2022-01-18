from pyteal import *

DOT_ALGO_APP_ID = 58724947
COST_FOR_3 = 250000000
COST_FOR_4 = 90000000
COST_FOR_5 = 15000000
DOT_ALGO_ESCROW_ADDRESS="HXZVYNLWCKLUGW7QW2WFDP57D5ZATV6L6DNENPNT5RSZ3JDNQPDIGGGB5Q"

def approval(name):

    is_valid_txn = Seq([
        
        Assert(
            Or(
                Global.group_size() == Int(2),
                Global.group_size() == Int(4)
            )
        ),
        
        Assert(Gtxn[0].sender() == Gtxn[1].sender()),
        Assert(Gtxn[0].receiver() == Addr(DOT_ALGO_ESCROW_ADDRESS)),

        If(Global.group_size() == Int(2))
        .Then(
            Assert(
                And(

                    Gtxn[1].application_id() == Int(DOT_ALGO_APP_ID),
                    Gtxn[1].sender() == Gtxn[0].sender(),
                    Gtxn[1].application_args[0] == Bytes("register_name"),
                    Gtxn[1].application_args[1] == Bytes(name)
                )
            )
        ).ElseIf(Global.group_size() == Int(4))
        .Then(
            Assert(
                And(

                    Gtxn[1].receiver() == Gtxn[2].sender(),
                    Gtxn[2].application_id() == Int(DOT_ALGO_APP_ID),
                    Gtxn[2].on_completion() == OnComplete.OptIn,
                    Gtxn[3].application_id() == Int(DOT_ALGO_APP_ID),
                    Gtxn[3].sender() == Gtxn[0].sender(),
                    Gtxn[3].application_args[0] == Bytes("register_name"),
                    Gtxn[3].application_args[1] == Bytes(name)
                )
            )
        ).Else(
            Return(Int(0))
        ),

        Int(1)     
    ])

    payment_for_3 = Seq([
        Assert(Gtxn[0].amount() >= Int(COST_FOR_3)),
        Assert(is_valid_txn),
        Int(1)
    ])

    payment_for_4 = Seq([
        Assert(Gtxn[0].amount() >= Int(COST_FOR_4)),
        Assert(is_valid_txn),
        Int(1)
    ])

    payment_for_5 = Seq([
        Assert(Gtxn[0].amount() >= Int(COST_FOR_5)),
        Assert(is_valid_txn),
        Int(1)
    ])

    program = Cond(
        [Len(Bytes(name)) == Int(3), payment_for_3],
        [Len(Bytes(name)) == Int(4), payment_for_4],
        [Len(Bytes(name)) >= Int(5), payment_for_5],
    )

    return program

with open('ans-dot-algo-name-record.teal', 'w') as f:
    compiled = compileTeal(approval("ans"), Mode.Signature, version=4)
    f.write(compiled)
