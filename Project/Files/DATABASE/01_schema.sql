-- =====================================================================
-- StyleHub Database - Schema (MySQL 8.0+)
-- Built from the StyleHub ERD + Business Requirements document.
-- Naming: PascalCase tables/columns so C# (Dapper/EF) and Python
-- (mysql-connector / SQLAlchemy) can map result columns directly.
-- =====================================================================

DROP DATABASE IF EXISTS StyleHub;
CREATE DATABASE StyleHub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE StyleHub;

-- ---------------------------------------------------------------------
-- CUSTOMER  (ERD: CustID, Name(First/Last), Email*, Phone*, PasswordHash)
-- ---------------------------------------------------------------------
CREATE TABLE Customer (
    CustID        INT AUTO_INCREMENT PRIMARY KEY,
    FirstName     VARCHAR(50)  NOT NULL,
    LastName      VARCHAR(50)  NOT NULL,
    Email         VARCHAR(100) NOT NULL UNIQUE,
    Phone         VARCHAR(20),
    PasswordHash  VARCHAR(255) NOT NULL,
    CreatedAt     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- EMPLOYEE  (ERD: EmpID, Email, Role, Name(First/Last))
-- ---------------------------------------------------------------------
CREATE TABLE Employee (
    EmpID         INT AUTO_INCREMENT PRIMARY KEY,
    FirstName     VARCHAR(50)  NOT NULL,
    LastName      VARCHAR(50)  NOT NULL,
    Email         VARCHAR(100) NOT NULL UNIQUE,
    PasswordHash  VARCHAR(255) NOT NULL,
    Role          ENUM('Manager','Tailor','Sales Associate') NOT NULL,
    CreatedAt     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- CATEGORY  (ERD: Category with Size, Color; Category 1 --< Product)
-- ---------------------------------------------------------------------
CREATE TABLE Category (
    CategoryID    INT AUTO_INCREMENT PRIMARY KEY,
    CategoryName  VARCHAR(50) NOT NULL,      -- e.g. Shirts, Dresses
    Size          VARCHAR(10) NOT NULL,      -- e.g. S, M, L, 32x30
    Color         VARCHAR(30) NOT NULL,
    UNIQUE (CategoryName, Size, Color)
);

-- ---------------------------------------------------------------------
-- PRODUCT  (ERD: ProductID, ProductName, PricePerUnit,
--           Quantity_In_Stock, ReorderPoint; requirements add Brand)
-- ---------------------------------------------------------------------
CREATE TABLE Product (
    ProductID        INT AUTO_INCREMENT PRIMARY KEY,
    CategoryID       INT NOT NULL,
    ProductName      VARCHAR(100)  NOT NULL,
    Brand            VARCHAR(50)   NOT NULL,
    PricePerUnit     DECIMAL(10,2) NOT NULL CHECK (PricePerUnit >= 0),
    QuantityInStock  INT NOT NULL DEFAULT 0 CHECK (QuantityInStock >= 0),
    ReorderPoint     INT NOT NULL DEFAULT 5,
    FOREIGN KEY (CategoryID) REFERENCES Category(CategoryID)
);

-- ---------------------------------------------------------------------
-- SUPPLIER  (ERD: SupplierID, SupplierName, ContactName, ContactEmail)
-- ---------------------------------------------------------------------
CREATE TABLE Supplier (
    SupplierID        INT AUTO_INCREMENT PRIMARY KEY,
    SupplierName      VARCHAR(100) NOT NULL,
    ContactFirstName  VARCHAR(50),
    ContactLastName   VARCHAR(50),
    ContactEmail      VARCHAR(100)
);

-- ---------------------------------------------------------------------
-- SUPPLIER PURCHASE  (ERD: Supplier 1 --Places--< SupplierPurchase)
-- ---------------------------------------------------------------------
CREATE TABLE SupplierPurchase (
    PurchaseID     INT AUTO_INCREMENT PRIMARY KEY,
    SupplierID     INT NOT NULL,
    PurchaseDate   DATE NOT NULL,
    ReceivedDate   DATE NULL,                -- NULL = not yet received
    FOREIGN KEY (SupplierID) REFERENCES Supplier(SupplierID)
);

-- ---------------------------------------------------------------------
-- SUPPLIER PURCHASE ITEM  (ERD: SupplierPurchase >-Contains-< Product, M:N resolved)
-- ---------------------------------------------------------------------
CREATE TABLE SupplierPurchaseItem (
    PurchaseID     INT NOT NULL,
    ProductID      INT NOT NULL,
    PricePerUnit   DECIMAL(10,2) NOT NULL CHECK (PricePerUnit >= 0),
    Quantity       INT NOT NULL CHECK (Quantity > 0),
    LineTotal      DECIMAL(12,2) AS (PricePerUnit * Quantity) STORED,
    PRIMARY KEY (PurchaseID, ProductID),
    FOREIGN KEY (PurchaseID) REFERENCES SupplierPurchase(PurchaseID) ON DELETE CASCADE,
    FOREIGN KEY (ProductID)  REFERENCES Product(ProductID)
);

-- ---------------------------------------------------------------------
-- ORDERS  (ERD: OrderID, OrderAmount, OrderDate, CompletionDate)
-- "Order" is a reserved word in SQL, so the table is named Orders.
-- ---------------------------------------------------------------------
CREATE TABLE Orders (
    OrderID         INT AUTO_INCREMENT PRIMARY KEY,
    CustID          INT NOT NULL,
    OrderDate       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CompletionDate  DATETIME NULL,
    OrderAmount     DECIMAL(10,2) NOT NULL DEFAULT 0,
    FOREIGN KEY (CustID) REFERENCES Customer(CustID)
);

-- ---------------------------------------------------------------------
-- ORDER ITEM  (ERD: Order >-Includes-< Product, M:N resolved)
-- UnitPrice is captured at time of sale so price changes don't alter history.
-- ---------------------------------------------------------------------
CREATE TABLE OrderItem (
    OrderID    INT NOT NULL,
    ProductID  INT NOT NULL,
    Quantity   INT NOT NULL CHECK (Quantity > 0),
    UnitPrice  DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (OrderID, ProductID),
    FOREIGN KEY (OrderID)   REFERENCES Orders(OrderID) ON DELETE CASCADE,
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID)
);

-- ---------------------------------------------------------------------
-- CART ITEM  (Requirements: PK = customer id + item id)
-- ---------------------------------------------------------------------
CREATE TABLE CartItem (
    CustID     INT NOT NULL,
    ProductID  INT NOT NULL,
    Quantity   INT NOT NULL DEFAULT 1 CHECK (Quantity > 0),
    AddedAt    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (CustID, ProductID),
    FOREIGN KEY (CustID)    REFERENCES Customer(CustID) ON DELETE CASCADE,
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID)
);

-- ---------------------------------------------------------------------
-- PAYMENT  (ERD: Orders 1 --Paid With-- 1 Payment)
-- Requirements: "Payment recording". One payment is recorded for each
-- order when it is placed. UNIQUE (OrderID) makes it one-to-one.
-- Only the last 4 card digits are stored -- never a full card number.
-- ---------------------------------------------------------------------
CREATE TABLE Payment (
    PaymentID      INT AUTO_INCREMENT PRIMARY KEY,
    OrderID        INT NOT NULL UNIQUE,
    PaymentMethod  ENUM('Credit Card','Debit Card','Cash','Gift Card') NOT NULL,
    CardLastFour   CHAR(4) NULL,
    Amount         DECIMAL(10,2) NOT NULL CHECK (Amount >= 0),
    PaymentDate    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (OrderID) REFERENCES Orders(OrderID) ON DELETE CASCADE,
    -- Business rule: a card payment must record the card's last 4 digits
    CHECK (PaymentMethod NOT IN ('Credit Card','Debit Card') OR CardLastFour IS NOT NULL)
);

-- ---------------------------------------------------------------------
-- ALTERATION  (ERD: AlterationID, AlterationName, Description,
--              AlterationPrice) -- the catalog of services offered
-- ---------------------------------------------------------------------
CREATE TABLE Alteration (
    AlterationID     INT AUTO_INCREMENT PRIMARY KEY,
    AlterationName   VARCHAR(50)  NOT NULL,
    Description      VARCHAR(255),
    AlterationPrice  DECIMAL(10,2) NOT NULL
);

-- ---------------------------------------------------------------------
-- ALTERATION ORDER  (ERD: Customer 1 --Places--< AlterationOrder,
--   Alteration 1 --Includes--< AlterationOrder,
--   Employee 1 --Completes--< AlterationOrder)
--
-- A customer brings in a piece of clothing (bought here or anywhere
-- else) and orders an alteration service for it. The alteration order
-- is NOT tied to a sales order, so there is no OrderID foreign key.
--   CustID             -> who requested the alteration
--   AlterationID       -> which service (hemming, sleeves, waist, ...)
--   EmpID              -> tailor assigned (NULL until assigned)
--   GarmentDescription -> the piece of clothing being altered
-- Requirements: service fee, assigned employee (nullable until
-- In Progress), status, pickup date.
-- ---------------------------------------------------------------------
CREATE TABLE AlterationOrder (
    AlterationOrderID   INT AUTO_INCREMENT PRIMARY KEY,
    CustID              INT NOT NULL,
    AlterationID        INT NOT NULL,
    EmpID               INT NULL,
    GarmentDescription  VARCHAR(255) NOT NULL,   -- e.g. 'Navy suit pants, 34x32'
    ServiceFee          DECIMAL(10,2) NOT NULL CHECK (ServiceFee >= 0),
    Status              ENUM('Received','In Progress','Ready for Pickup','Completed')
                        NOT NULL DEFAULT 'Received',
    RequestDate         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PickupDate          DATETIME NULL,
    FOREIGN KEY (CustID)       REFERENCES Customer(CustID),
    FOREIGN KEY (AlterationID) REFERENCES Alteration(AlterationID),
    FOREIGN KEY (EmpID)        REFERENCES Employee(EmpID),
    -- Business rule: must be assigned before it can move past 'Received'
    CHECK (Status = 'Received' OR EmpID IS NOT NULL)
);

-- Helpful indexes for the report queries / app filters
CREATE INDEX IX_Orders_OrderDate   ON Orders(OrderDate);
CREATE INDEX IX_Product_Name_Brand ON Product(ProductName, Brand);
CREATE INDEX IX_AltOrder_Status    ON AlterationOrder(Status);
