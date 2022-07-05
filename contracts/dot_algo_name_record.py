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

def ValidateRecord(name, reg_app_id, reg_escrow_acct):

    DOT_ALGO_APP_ID = reg_app_id
    DOT_ALGO_ESCROW_ADDRESS = reg_escrow_acct
    
    i = ScratchVar(TealType.uint64)

    is_valid_txn = Seq([

        Assert(Len(Bytes(name)) <= Int(64)),
        For(i.store(Int(0)), i.load() < Len(Bytes(name)), i.store(i.load() + Int(1))).Do(
            Assert(
                Or(
                    And(
                        GetByte(Bytes(name), i.load()) >= Int(constants.ASCII_LOWER_CASE_A),
                        GetByte(Bytes(name), i.load()) <= Int(constants.ASCII_LOWER_CASE_Z)
                    ),
                    And(
                        GetByte(Bytes(name), i.load()) >= Int(constants.ASCII_DIGIT_0),
                        GetByte(Bytes(name), i.load()) <= Int(constants.ASCII_DIGIT_9)
                    )
                )
            )
        ),
        
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
        Assert(Gtxn[0].amount() >= Int(constants.COST_FOR_3)),
        Assert(is_valid_txn),
        Int(1)
    ])

    payment_for_4 = Seq([
        Assert(Gtxn[0].amount() >= Int(constants.COST_FOR_4)),
        Assert(is_valid_txn),
        Int(1)
    ])

    payment_for_5 = Seq([
        Assert(Gtxn[0].amount() >= Int(constants.COST_FOR_5)),
        Assert(is_valid_txn),
        Int(1)
    ])

    program = Cond(
        [Len(Bytes(name)) == Int(3), payment_for_3],
        [Len(Bytes(name)) == Int(4), payment_for_4],
        [Len(Bytes(name)) >= Int(5), payment_for_5],
    )

    return program
