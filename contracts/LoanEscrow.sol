// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract LoanEscrow {

    enum LoanStatus {
        Created,
        Funded,
        Repaid
    }

    struct Loan {
        address borrower;
        address lender;
        uint256 amount;      // Amount in wei
        uint256 months;
        uint256 createdAt;
        LoanStatus status;
    }

    uint256 public nextId = 1;

    mapping(uint256 => Loan) public loans;

    event LoanCreated(
        uint256 indexed loanId,
        address indexed borrower,
        uint256 amount,
        uint256 months
    );

    event LoanFunded(
        uint256 indexed loanId,
        address indexed lender,
        uint256 amount
    );

    event LoanRepaid(
        uint256 indexed loanId,
        address indexed borrower,
        uint256 amount
    );

    // Borrower creates loan request
    function createLoan(
        uint256 amount,
        uint256 months
    ) external returns (uint256) {

        require(amount > 0, "invalid amount");
        require(months > 0, "invalid months");

        uint256 loanId = nextId++;

        loans[loanId] = Loan({
            borrower: msg.sender,
            lender: address(0),
            amount: amount,
            months: months,
            createdAt: block.timestamp,
            status: LoanStatus.Created
        });

        emit LoanCreated(
            loanId,
            msg.sender,
            amount,
            months
        );

        return loanId;
    }

    // Lender funds the loan
    function fundLoan(
        uint256 loanId
    ) external payable {

        Loan storage loan = loans[loanId];

        require(
            loan.status == LoanStatus.Created,
            "loan not available"
        );

        require(
            msg.value == loan.amount,
            "incorrect amount"
        );

        require(
            msg.sender != loan.borrower,
            "borrower cannot fund own loan"
        );

        loan.lender = msg.sender;
        loan.status = LoanStatus.Funded;

        payable(loan.borrower).transfer(msg.value);

        emit LoanFunded(
            loanId,
            msg.sender,
            msg.value
        );
    }

    // Borrower repays lender
    function repayLoan(
        uint256 loanId
    ) external payable {

        Loan storage loan = loans[loanId];

        require(
            loan.status == LoanStatus.Funded,
            "loan not funded"
        );

        require(
            msg.sender == loan.borrower,
            "only borrower"
        );

        require(
            msg.value == loan.amount,
            "repay exact amount"
        );

        loan.status = LoanStatus.Repaid;

        payable(loan.lender).transfer(msg.value);

        emit LoanRepaid(
            loanId,
            msg.sender,
            msg.value
        );
    }

    // Helper function for frontend
    function getLoan(
        uint256 loanId
    )
        external
        view
        returns (
            address borrower,
            address lender,
            uint256 amount,
            uint256 months,
            uint256 createdAt,
            LoanStatus status
        )
    {
        Loan memory loan = loans[loanId];

        return (
            loan.borrower,
            loan.lender,
            loan.amount,
            loan.months,
            loan.createdAt,
            loan.status
        );
    }
}