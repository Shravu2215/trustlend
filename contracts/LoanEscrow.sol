// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract LoanEscrow {
    struct Loan {
        address borrower;
        uint256 amount;
        uint256 months;
        uint256 createdAt;
    }

    uint256 public nextId = 1;
    mapping(uint256 => Loan) public loans;

    event LoanCreated(uint256 indexed loanId, address indexed borrower, uint256 amount, uint256 months);

    function createLoan(address borrower, uint256 amount, uint256 months) public returns (uint256) {
        require(borrower != address(0), "invalid borrower");
        require(amount > 0, "invalid amount");
        require(months > 0, "invalid months");

        uint256 loanId = nextId++;
        loans[loanId] = Loan({
            borrower: borrower,
            amount: amount,
            months: months,
            createdAt: block.timestamp
        });

        emit LoanCreated(loanId, borrower, amount, months);
        return loanId;
    }
}
