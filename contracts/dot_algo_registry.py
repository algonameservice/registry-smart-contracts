from pyteal import *

COST_FOR_3 = 250000000
COST_FOR_4 = 90000000
COST_FOR_5 = 15000000
COST_FOR_RENEWAL = 5000000
RENEWAL_TIME = 86400*365

def approval_program():
    on_creation = Seq([
        App.globalPut(Bytes("Creator"), Txn.sender()),
        Return(Int(1))
    ])

    is_valid_txn = Seq([
        
        Assert(
            Or(
                Global.group_size() == Int(2),
                Global.group_size() == Int(4)
            )
        ),
        
        Assert(Gtxn[0].sender() == Gtxn[1].sender()),
        Assert(Gtxn[0].receiver() == Global.current_application_address()),

        If(Global.group_size() == Int(2))
        .Then(
            Assert(
                And(

                    Gtxn[1].application_id() == Global.current_application_id(),
                    Gtxn[1].sender() == Gtxn[0].sender(),
                    Gtxn[1].application_args[0] == Bytes("register_name")
                )
            )
        ).ElseIf(Global.group_size() == Int(4))
        .Then(
            Assert(
                And(

                    Gtxn[1].receiver() == Gtxn[2].sender(),
                    Gtxn[2].application_id() == Global.current_application_id(),
                    Gtxn[2].on_completion() == OnComplete.OptIn,
                    Gtxn[3].application_id() == Global.current_application_id(),
                    Gtxn[3].sender() == Gtxn[0].sender(),
                    Gtxn[3].application_args[0] == Bytes("register_name")
                )
            )
        ).Else(
            Return(Int(0))
        ),
        
        Int(1)     
    ])
    
    get_arg_1 = Txn.application_args[1]
    get_arg_2 = Txn.application_args[2]
    
    number_of_years = Minus(Btoi(get_arg_2), Int(1))

    get_name_status = App.localGetEx(Int(1), Txn.application_id(), Bytes("owner"))
    is_name_owner = App.localGet(Int(1), Bytes("owner"))
    current_expiry = App.localGet(Int(1), Bytes("expiry"))

    new_expiry = Add(current_expiry, Mul(Btoi(get_arg_1), Int(RENEWAL_TIME)))

    contract_creator = App.globalGet(Bytes("Creator"))
    
    update_name = Seq([
        Assert(is_name_owner == Txn.sender()),
        App.localPut(Int(1),get_arg_1, get_arg_2),
        Return(Int(1))
    ])

    renew_name = Seq([
        Assert(is_name_owner == Txn.sender()),
        Assert(Txn.amount() == Mul(Btoi(get_arg_1), Int(COST_FOR_RENEWAL))),
        App.localPut(Int(1),Bytes("expiry"), new_expiry),
        Return(Int(1))
    ])
    
    register_name = Seq([

        Assert(is_valid_txn),
        get_name_status,        
        Assert(
            Or(
                get_name_status.hasValue() == Int(0),
                Global.latest_timestamp() >= current_expiry
            )
        ),

        Assert(number_of_years <= Int(10)),

        Assert(
            Or(
                And(
                    Len(get_arg_2) == Int(3), 
                    Gtxn[0].amount() >= Add(Int(COST_FOR_3), Mul(number_of_years, Int(COST_FOR_RENEWAL)))
                ),
                And(
                    Len(get_arg_2) == Int(4), 
                    Gtxn[0].amount() >= Add(Int(COST_FOR_4), Mul(number_of_years, Int(COST_FOR_RENEWAL)))
                ),
                And(
                    Len(get_arg_2) >= Int(5), 
                    Gtxn[0].amount() >= Add(Int(COST_FOR_5), Mul(number_of_years, Int(COST_FOR_RENEWAL)))
                )
            )
        ),

        App.localPut(Int(1), Bytes("owner"), Txn.sender()),
        App.localPut(Int(1), Bytes("expiry"), Add(Global.latest_timestamp(), Mul(Int(RENEWAL_TIME), Add(number_of_years, Int(1))))),
        App.localPut(Int(1), Bytes("subdomain"), Int(0)),
        Return(Int(1))
    ])

    withdraw_funds = Seq(
        Assert(Txn.sender() == contract_creator),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: Txn.sender(),
                TxnField.amount: Btoi(Txn.application_args[1]),
            }
        ),
        InnerTxnBuilder.Submit(),
        Return(Int(1))
    )

    update_or_delete_application = Seq([
        Assert(Txn.sender() == contract_creator),
        Return(Int(1))
    ])

    #MUST REMOVE:
    expire = Seq([
        Assert(Txn.sender() == contract_creator),
        App.localPut(Int(1), Bytes("expiry"), Int(1)),
        Return(Int(1))
    ])


    program = Cond(
        [Txn.application_id() == Int(0), on_creation],
        [Txn.on_completion() == OnComplete.OptIn, Return(Int(1))],
        [Txn.on_completion() == OnComplete.UpdateApplication, update_or_delete_application],
        [Txn.on_completion() == OnComplete.DeleteApplication, update_or_delete_application],
        [Txn.application_args[0] == Bytes("register_name"), register_name],
        [Txn.application_args[0] == Bytes("update_name"), update_name],
        [Txn.application_args[0] == Bytes("renew_name"), renew_name],
        [Txn.application_args[0] == Bytes("withdraw_funds"), withdraw_funds],
        #MUST REMOVE
        [Txn.application_args[0] == Bytes("force_expire"), expire]
    )

    return program

def clear_state_program():
    return Int(1) 

with open('dot_algo_registry_approval.teal', 'w') as f:
    compiled = compileTeal(approval_program(), Mode.Application, version=5)
    f.write(compiled)

with open('dot_algo_registry_clear_state.teal', 'w') as f:
    compiled = compileTeal(clear_state_program(), Mode.Application, version=5)
    f.write(compiled)

