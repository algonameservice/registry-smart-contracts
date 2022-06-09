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

from pyteal import *
from . import constants

def approval_program(account):

    get_arg_1 = Txn.application_args[1]
    get_arg_2 = Txn.application_args[2]
    
    number_of_years = Minus(Btoi(get_arg_2), Int(1))

    get_name_status = App.localGetEx(Int(1), Txn.application_id(), Bytes("owner"))
    is_name_owner = App.localGet(Int(1), Bytes("owner"))
    current_expiry = App.localGet(Int(1), Bytes("expiry"))
    domain_name = App.localGet(Int(1), Bytes("name"))

    new_expiry = Add(current_expiry, Mul(Btoi(get_arg_1), Int(constants.RENEWAL_TIME)))
    property_to_delete = App.localGetEx(Int(1), App.id(), Txn.application_args[1])

    on_creation = Seq([
        App.globalPut(Bytes("name_controller"), Addr(account)),
        Return(Int(1))
    ])

    i = ScratchVar(TealType.uint64)

    @Subroutine(TealType.uint64)
    def basic_txn_checks():
        return Seq([
            For(i.store(Int(0)), i.load() < Global.group_size(), i.store(i.load() + Int(1))).Do(
                Assert(
                    And(
                        Gtxn[i.load()].rekey_to() == Global.zero_address(),
                        Gtxn[i.load()].applications.length() == Int(0),
                        Gtxn[i.load()].assets.length() == Int(0),
                        Gtxn[i.load()].fee() <= Int(1000)
                    )
                )
            ),
            Return(Int(1))
        ])

    @Subroutine(TealType.uint64)
    def check_closeremndr(index):
        return Seq([
            Assert(Gtxn[index].close_remainder_to() == Global.zero_address()),
            Return(Int(1))
        ])

    @Subroutine(TealType.uint64)
    def check_app_args_size(txn_index, size):
        return Seq([
            Assert(Gtxn[txn_index].application_args.length() == size),
            Return(Int(1))
        ])

    @Subroutine(TealType.uint64)
    def check_app_accts_size(txn_index, size):
        return Seq([
            Assert(Gtxn[txn_index].accounts.length() == size),
            Return(Int(1))
        ])        

    @Subroutine(TealType.uint64)
    def reset_domain_properties():
        return Seq([
            discord := App.localGetEx(Int(1), Txn.application_id(), Bytes("discord")),
            discord,
            If(discord.hasValue()).Then(App.localDel(Int(1), Bytes("discord"))),
            github := App.localGetEx(Int(1), Txn.application_id(), Bytes("github")),
            github,
            If(github.hasValue()).Then(App.localDel(Int(1), Bytes("github"))),
            twitter := App.localGetEx(Int(1), Txn.application_id(), Bytes("twitter")),
            twitter,
            If(twitter.hasValue()).Then(App.localDel(Int(1), Bytes("twitter"))),
            reddit := App.localGetEx(Int(1), Txn.application_id(), Bytes("reddit")),
            reddit,
            If(reddit.hasValue()).Then(App.localDel(Int(1), Bytes("reddit"))),
            telegram := App.localGetEx(Int(1), Txn.application_id(), Bytes("telegram")),
            telegram,
            If(telegram.hasValue()).Then(App.localDel(Int(1), Bytes("telegram"))),
            youtube := App.localGetEx(Int(1), Txn.application_id(), Bytes("youtube")),
            youtube,
            If(youtube.hasValue()).Then(App.localDel(Int(1), Bytes("youtube"))),
            avatar := App.localGetEx(Int(1), Txn.application_id(), Bytes("avatar")),
            avatar,
            If(avatar.hasValue()).Then(App.localDel(Int(1), Bytes("avatar"))),
            content := App.localGetEx(Int(1), Txn.application_id(), Bytes("content")),
            content,
            If(content.hasValue()).Then(App.localDel(Int(1), Bytes("content"))),
            ipaddress := App.localGetEx(Int(1), Txn.application_id(), Bytes("ipaddress")),
            ipaddress,
            If(ipaddress.hasValue()).Then(App.localDel(Int(1), Bytes("ipaddress"))),
            is_default := App.localGetEx(Int(1), Txn.application_id(), Bytes("is_default")),
            is_default,
            If(is_default.hasValue()).Then(App.localDel(Int(1), Bytes("is_default"))),
            Return(Int(1))
        ])           
        
    is_valid_registration_txn = Seq([
        
        Assert(check_closeremndr(Int(0)) == Int(1)),
        Assert(basic_txn_checks() == Int(1)),
        
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
                    check_app_accts_size(Int(1), Int(1)),
                    check_app_args_size(Int(1), Int(3)) == Int(1),
                    Gtxn[1].application_id() == Global.current_application_id(),
                    Gtxn[1].sender() == Gtxn[0].sender(),
                    Gtxn[1].application_args[0] == Bytes("register_name")
                )
            )
        ).ElseIf(Global.group_size() == Int(4))
        .Then(
            Assert(
                And(
                    check_app_accts_size(Int(2), Int(0)),
                    check_app_accts_size(Int(3), Int(1)),
                    check_closeremndr(Int(1)) == Int(1),
                    check_app_args_size(Int(3), Int(3)) == Int(1),
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
    
    is_valid_renewal_txn = And(
        basic_txn_checks() == Int(1),
        check_app_args_size(Int(1), Int(2)) == Int(1),
        check_app_accts_size(Int(1), Int(1)) == Int(1),
        check_closeremndr(Int(0)) == Int(1),
        Global.group_size() == Int(2),
        Gtxn[0].type_enum() == TxnType.Payment,
        Gtxn[0].sender() == is_name_owner,
        Gtxn[0].receiver() == Global.current_application_address(),
        Gtxn[1].sender() == Gtxn[0].sender()
    )

    is_valid_delete_prop_txn = And(
        basic_txn_checks() == Int(1),
        Txn.application_args.length() == Int(2),        
        Txn.application_args[1] != Bytes("name"),
        Txn.application_args[1] != Bytes("owner"),
        Txn.application_args[1] != Bytes("expiry"),
        Txn.application_args[1] != Bytes("transfer_price"),
        Txn.application_args[1] != Bytes("transfer_to"),
        Txn.application_args[1] != Bytes("subdomain"),
        Txn.application_args[1] != Bytes("value")
    )

    register_name = Seq([

        Assert(is_valid_registration_txn),
        get_name_status,        
        Assert(
            Or(
                get_name_status.hasValue() == Int(0),
                Global.latest_timestamp() >= current_expiry
            )
        ),

        Assert(
            
            Or(
                And(
                    Len(Txn.application_args[1]) == Int(3), 
                    Gtxn[0].amount() >= Add(Int(constants.COST_FOR_3), Mul(number_of_years, Int(constants.COST_FOR_3)))
                ),
                And(
                    Len(Txn.application_args[1]) == Int(4), 
                    Gtxn[0].amount() >= Add(Int(constants.COST_FOR_4), Mul(number_of_years, Int(constants.COST_FOR_4)))
                ),
                And(
                    Len(Txn.application_args[1]) >= Int(5), 
                    Gtxn[0].amount() >= Add(Int(constants.COST_FOR_5), Mul(number_of_years, Int(constants.COST_FOR_5)))
                )
            )
        ),

        App.localPut(Int(1), Bytes("owner"), Txn.sender()),
        App.localPut(Int(1), Bytes("expiry"), Add(Global.latest_timestamp(), Mul(Int(constants.RENEWAL_TIME), Add(number_of_years, Int(1))))),
        App.localPut(Int(1), Bytes("subdomain"), Int(0)),
        App.localPut(Int(1), Bytes("transfer_price"), Bytes("")),
        App.localPut(Int(1), Bytes("transfer_to"), Bytes("")),
        App.localPut(Int(1), Bytes("value"), Txn.sender()),
        App.localPut(Int(1), Bytes("name"), Txn.application_args[1]),
        Return(Int(1))
    ])

    renew_name = Seq([
        Assert(is_valid_renewal_txn),
        If(Len(domain_name) == Int(3))
        .Then(
            Assert(Gtxn[0].amount() == Mul(Btoi(get_arg_1), Int(constants.COST_FOR_3)))
        ).ElseIf(Len(domain_name) == Int(4))
        .Then(
            Assert(Gtxn[0].amount() == Mul(Btoi(get_arg_1), Int(constants.COST_FOR_4)))
        ).ElseIf(Len(domain_name) >= Int(5))
        .Then(
            Assert(Gtxn[0].amount() == Mul(Btoi(get_arg_1), Int(constants.COST_FOR_5)))
        ),
        App.localPut(Int(1),Bytes("expiry"), new_expiry),
        Return(Int(1))
    ])
    
    update_name = Seq([
        Assert(basic_txn_checks() == Int(1)),
        Assert(Txn.application_args.length() == Int(3)),
        Assert(Txn.accounts.length() == Int(1)),                
        Assert(get_arg_1 != Bytes("name")),
        Assert(get_arg_1 != Bytes("owner")),
        Assert(get_arg_1 != Bytes("expiry")),
        Assert(get_arg_1 != Bytes("transfer_price")),
        Assert(get_arg_1 != Bytes("transfer_to")),
        Assert(get_arg_1 != Bytes("value")),
        Assert(is_name_owner == Txn.sender()),
        App.localPut(Int(1), get_arg_1, get_arg_2),
        Return(Int(1))
    ])

    update_resolver_account = Seq([
        Assert(basic_txn_checks() == Int(1)),
        Assert(Global.group_size() == Int(1)),
        Assert(Txn.application_args.length() == Int(1)),
        Assert(is_name_owner == Txn.sender()),
        App.localPut(Int(1), Bytes("value"), Txn.accounts[2]),
        Return(Int(1))
    ])

    set_default_account = Seq([
        Assert(basic_txn_checks() == Int(1)),
        Assert(is_name_owner == Txn.sender()),
        Assert(Txn.application_args.length() == Int(1)),
        Assert(Txn.accounts.length() == Int(1)),
        App.localPut(Int(1), Bytes("is_default"), Int(1)),
        Return(Int(1))
    ])

    remove_property = Seq([
        Assert(is_valid_delete_prop_txn),
        Assert(is_name_owner == Txn.sender()),
        property_to_delete,
        If(property_to_delete.hasValue(),
            App.localDel(Int(1), Txn.application_args[1]),
            Return(Int(0))
        ),
        Return(Int(1))
    ])

    initiate_transfer = Seq([
        Assert(basic_txn_checks() == Int(1)),
        Assert(check_app_args_size(Int(0), Int(2))),
        Assert(check_app_accts_size(Int(0), Int(2))),
        Assert(Global.group_size() == Int(1)),
        Assert(is_name_owner == Txn.sender()),
        App.localPut(Int(1), Bytes("transfer_price"), Btoi(Txn.application_args[1])),
        App.localPut(Int(1), Bytes("transfer_to"), Txn.accounts[2]),
        Return(Int(1))
    ])

    withdraw_transfer = Seq([
        Assert(basic_txn_checks() == Int(1)),
        Assert(is_name_owner == Txn.sender()),
        Assert(Txn.application_args.length() == Int(1)),
        Assert(Txn.accounts.length() == Int(1)),
        App.localPut(Int(1), Bytes("transfer_price"), Int(0)),
        App.localPut(Int(1), Bytes("transfer_to"), Bytes("")),
        Return(Int(1))
    ])

    accept_transfer = Seq([
        Assert(basic_txn_checks() == Int(1)),
        Assert(check_app_args_size(Int(2), Int(1))),
        Assert(check_app_accts_size(Int(2), Int(1))),
        Assert(Global.group_size() == Int(3)),
        Assert(Gtxn[0].receiver() == is_name_owner),
        Assert(Gtxn[0].rekey_to() == Global.zero_address()),
        Assert(check_closeremndr(Int(0)) == Int(1)),
        Assert(Gtxn[0].amount() == App.localGet(Int(1), Bytes("transfer_price"))),
        Assert(Gtxn[0].sender() == App.localGet(Int(1), Bytes("transfer_to"))),
        Assert(Gtxn[0].sender() == Gtxn[1].sender()),
        Assert(Gtxn[0].sender() == Gtxn[2].sender()),
        Assert(Gtxn[1].receiver() == Global.current_application_address()),
        Assert(Gtxn[1].amount() == Int(constants.COST_FOR_TRANSFER)),
        Assert(Gtxn[1].rekey_to() == Global.zero_address()),
        Assert(check_closeremndr(Int(1)) == Int(1)),
        Assert(reset_domain_properties() == Int(1)),
        App.localPut(Int(1), Bytes("owner"), Gtxn[0].sender()),
        App.localPut(Int(1), Bytes("value"), Gtxn[0].sender()),
        App.localPut(Int(1), Bytes("transfer_to"), Bytes("")),
        App.localPut(Int(1), Bytes("transfer_price"), Int(0)),
        App.localPut(Int(1), Bytes("subdomain"), Int(0)),
        Return(Int(1))
    ])

    withdraw_funds = Seq(
        Assert(basic_txn_checks() == Int(1)),
        Assert(Txn.sender() == App.globalGet(Bytes("name_controller"))),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: Txn.accounts[1],
                TxnField.amount: Btoi(Txn.application_args[1]),
                TxnField.fee: Int(1000)
            }
        ),
        InnerTxnBuilder.Submit(),
        Return(Int(1))
    )

    update_or_delete_application = Seq([
        Assert(basic_txn_checks() == Int(1)),
        Assert(Txn.sender() == App.globalGet(Bytes("name_controller"))),
        Return(Int(1))
    ])

    update_global_state = Seq([
        Assert(basic_txn_checks() == Int(1)),
        Assert(Txn.sender() == App.globalGet(Bytes("name_controller"))),
        App.globalPut(get_arg_1, get_arg_2),
        Return(Int(1))
    ])

    program = Cond(
        [Txn.application_id() == Int(0), on_creation],
        [Txn.on_completion() == OnComplete.OptIn, Return(Int(1))],
        [Txn.on_completion() == OnComplete.UpdateApplication, update_or_delete_application],
        [Txn.on_completion() == OnComplete.DeleteApplication, update_or_delete_application],
        [Txn.on_completion() == OnComplete.CloseOut, Return(Int(0))],
        [Txn.on_completion() == OnComplete.ClearState, Return(Int(0))],
        [Txn.application_args[0] == Bytes("update_global_state"), update_global_state],
        [Txn.application_args[0] == Bytes("register_name"), register_name],
        [Txn.application_args[0] == Bytes("update_name"), update_name],
        [Txn.application_args[0] == Bytes("remove_property"), remove_property],
        [Txn.application_args[0] == Bytes("renew_name"), renew_name],
        [Txn.application_args[0] == Bytes("update_resolver_account"), update_resolver_account],
        [Txn.application_args[0] == Bytes("set_default_account"), set_default_account],
        [Txn.application_args[0] == Bytes("initiate_transfer"), initiate_transfer],
        [Txn.application_args[0] == Bytes("accept_transfer"), accept_transfer],
        [Txn.application_args[0] == Bytes("withdraw_transfer"), withdraw_transfer],
        [Txn.application_args[0] == Bytes("withdraw_funds"), withdraw_funds]
        
    )

    return program

def clear_state_program():
    return Int(1) 

with open('dot_algo_registry_approval.teal', 'w') as f:
    compiled = compileTeal(approval_program('PD2CGHFAZZQNYBRPZH7HNTA275K3FKZPENRSUXWZHBIVNPHVDFHLNIUSXU'), Mode.Application, version=5)
    f.write(compiled)

with open('dot_algo_registry_clear_state.teal', 'w') as f:
    compiled = compileTeal(clear_state_program(), Mode.Application, version=5)
    f.write(compiled)

