-- =====================================================================
-- StyleHub Database - Sample Data (for testing reports and the web app)
-- Run after 01_schema.sql
-- =====================================================================
USE StyleHub;

INSERT INTO Customer (FirstName, LastName, Email, Phone, PasswordHash, CreatedAt) VALUES
('Ava',    'Johnson',  'ava.johnson@email.com',  '555-201-1001', 'hash_ava',    '2026-01-05'),
('Liam',   'Smith',    'liam.smith@email.com',   '555-201-1002', 'hash_liam',   '2026-01-18'),
('Mia',    'Brown',    'mia.brown@email.com',    '555-201-1003', 'hash_mia',    '2026-02-02'),
('Noah',   'Davis',    'noah.davis@email.com',   '555-201-1004', 'hash_noah',   '2026-02-20'),
('Emma',   'Wilson',   'emma.wilson@email.com',  '555-201-1005', 'hash_emma',   '2026-03-11'),
('Lucas',  'Moore',    'lucas.moore@email.com',  '555-201-1006', 'hash_lucas',  '2026-04-07'),
('Sophia', 'Taylor',   'sophia.taylor@email.com','555-201-1007', 'hash_sophia', '2026-05-15'),
('Ethan',  'Anderson', 'ethan.anderson@email.com','555-201-1008','hash_ethan',  '2026-06-01');

INSERT INTO Employee (FirstName, LastName, Email, PasswordHash, Role, CreatedAt) VALUES
('Grace',  'Lee',     'grace.lee@stylehub.com',     'hash_e1', 'Manager',         '2025-08-01'),
('Marcus', 'Hill',    'marcus.hill@stylehub.com',   'hash_e2', 'Tailor',          '2025-09-15'),
('Priya',  'Patel',   'priya.patel@stylehub.com',   'hash_e3', 'Tailor',          '2025-11-03'),
('Diego',  'Ramirez', 'diego.ramirez@stylehub.com', 'hash_e4', 'Tailor',          '2026-02-10'),
('Hannah', 'Clark',   'hannah.clark@stylehub.com',  'hash_e5', 'Sales Associate', '2026-03-01');

INSERT INTO Category (CategoryName, Size, Color) VALUES
('Shirts',  'M',     'White'),   -- 1
('Shirts',  'L',     'Blue'),    -- 2
('Pants',   '32x30', 'Khaki'),   -- 3
('Pants',   '34x32', 'Black'),   -- 4
('Dresses', 'S',     'Red'),     -- 5
('Dresses', 'M',     'Black'),   -- 6
('Jackets', 'L',     'Navy'),    -- 7
('Suits',   '40R',   'Charcoal');-- 8

INSERT INTO Product (CategoryID, ProductName, Brand, PricePerUnit, QuantityInStock, ReorderPoint) VALUES
(1, 'Classic Oxford Shirt',   'Northline',  39.99, 25, 10),  -- 1
(2, 'Slim Fit Dress Shirt',   'Northline',  44.99,  6, 10),  -- 2  below reorder
(3, 'Chino Pants',            'Urban Thread',49.99, 18,  8), -- 3
(4, 'Tailored Trousers',      'Urban Thread',69.99,  3,  6), -- 4  below reorder
(5, 'Wrap Midi Dress',        'Bella Rose', 79.99, 12,  5),  -- 5
(6, 'Little Black Dress',     'Bella Rose', 89.99,  2,  5),  -- 6  below reorder
(7, 'Wool Blend Blazer',      'Crestwood', 149.99,  9,  4),  -- 7
(8, 'Two-Piece Business Suit','Crestwood', 299.99,  4,  3),  -- 8
(1, 'Linen Casual Shirt',     'Coastal Co', 34.99, 30, 10),  -- 9  slow mover
(5, 'Summer Sundress',        'Coastal Co', 59.99, 20,  6);  -- 10 never sold

INSERT INTO Supplier (SupplierName, ContactFirstName, ContactLastName, ContactEmail) VALUES
('Northline Apparel Wholesale', 'Karen', 'Mills',  'kmills@northline.com'),
('Urban Thread Distributors',   'James', 'Ortega', 'jortega@urbanthread.com'),
('Bella Rose Fashions',         'Nina',  'Russo',  'nina@bellarose.com'),
('Crestwood Menswear Supply',   'Paul',  'Grant',  'pgrant@crestwood.com');

INSERT INTO SupplierPurchase (SupplierID, PurchaseDate, ReceivedDate) VALUES
(1, '2026-01-10', '2026-01-17'),
(2, '2026-01-12', '2026-01-20'),
(3, '2026-01-20', '2026-01-28'),
(1, '2026-02-01', '2026-02-09'),
(4, '2026-02-05', '2026-02-19'),
(2, '2026-02-15', '2026-02-24'),
(3, '2026-03-01', '2026-03-12'),
(3, '2026-04-02', '2026-04-10'),
(2, '2026-10-20', NULL);          -- open PO, not received

INSERT INTO SupplierPurchaseItem (PurchaseID, ProductID, PricePerUnit, Quantity) VALUES
(1, 1,  18.00, 40), (1, 2, 21.00, 30),
(2, 3,  22.00, 30),
(3, 5,  36.00, 25),
(4, 9,  15.00, 35),
(5, 7,  70.00, 15), (5, 8, 140.00, 10),
(6, 4,  31.00, 20),
(7, 6,  40.00, 20),
(8, 10, 26.00, 20),
(9, 4,  31.00, 15), (9, 3, 22.00, 10);

-- Orders (OrderAmount = sum of the items purchased; recalculated at the bottom)
INSERT INTO Orders (CustID, OrderDate, CompletionDate, OrderAmount) VALUES
(1, '2026-02-03 10:15', '2026-02-03 10:20', 129.97), -- 1
(2, '2026-02-14 14:02', '2026-02-14 14:10', 314.99), -- 2
(3, '2026-03-05 11:30', '2026-03-05 11:35', 179.98), -- 3
(1, '2026-03-22 16:45', '2026-03-22 16:50', 164.97), -- 4
(4, '2026-04-10 09:05', '2026-04-10 09:12', 344.98), -- 5
(5, '2026-05-01 13:20', '2026-05-01 13:25', 104.98), -- 6
(2, '2026-06-12 15:00', '2026-06-12 15:05', 189.97), -- 7
(6, '2026-07-04 12:10', '2026-07-04 12:15',  89.98), -- 8
(3, '2026-08-19 17:40', '2026-08-19 17:45', 259.97), -- 9
(1, '2026-09-08 10:00', '2026-09-08 10:06', 384.97), -- 10
(7, '2026-10-02 11:11', '2026-10-02 11:15', 134.98), -- 11
(4, '2026-10-25 14:30', NULL,               164.99); -- 12 still open

INSERT INTO OrderItem (OrderID, ProductID, Quantity, UnitPrice) VALUES
(1, 1, 2, 39.99), (1, 3, 1, 49.99),
(2, 8, 1, 299.99),
(3, 6, 2, 89.99),
(4, 2, 2, 44.99), (4, 3, 1, 49.99),
(5, 7, 1, 149.99), (5, 5, 2, 79.99),
(6, 1, 1, 39.99), (6, 2, 1, 44.99),
(7, 4, 2, 69.99), (7, 2, 1, 44.99),
(8, 2, 2, 44.99),
(9, 6, 2, 89.99), (9, 5, 1, 79.99),
(10, 8, 1, 299.99), (10, 2, 1, 44.99), (10, 1, 1, 39.99),
(11, 4, 1, 69.99), (11, 9, 1, 34.99),
(12, 7, 1, 149.99);

-- Shopping carts: items customers have added but not ordered yet.
-- (Ava, customer 1, is left empty so the demo starts with a clean cart.)
INSERT INTO CartItem (CustID, ProductID, Quantity, AddedAt) VALUES
(3,  9, 2, '2026-10-30 18:05'),
(3,  1, 1, '2026-10-30 18:07'),
(5,  3, 1, '2026-11-01 12:40'),
(6, 10, 1, '2026-11-02 09:15'),
(8,  7, 1, '2026-11-03 20:30');

INSERT INTO Alteration (AlterationName, Description, AlterationPrice) VALUES
('Hem Pants',        'Shorten or lengthen pant hem',          15.00), -- 1
('Take In Waist',    'Reduce waist size on pants or skirts',  20.00), -- 2
('Sleeve Shortening','Shorten jacket or shirt sleeves',       25.00), -- 3
('Dress Hem',        'Adjust dress length',                   30.00), -- 4
('Suit Tailoring',   'Full fit adjustment for suit jacket',   60.00); -- 5

-- Alteration orders: a customer orders an alteration to a piece of clothing.
-- They are NOT linked to a sales order -- the garment may have been bought
-- at StyleHub or somewhere else (see rows marked "brought in").
INSERT INTO AlterationOrder (CustID, AlterationID, EmpID, GarmentDescription, ServiceFee, Status, RequestDate, PickupDate) VALUES
(2, 5, 2,    'Charcoal two-piece suit jacket, 40R',          15.00, 'Completed',        '2026-02-14 14:10', '2026-02-21 12:00'), -- discounted
(1, 1, 3,    'Khaki chino pants, 32x30',                     15.00, 'Completed',        '2026-03-22 16:50', '2026-03-26 10:00'),
(4, 3, 2,    'Navy wool blend blazer, L',                    25.00, 'Completed',        '2026-04-10 09:12', '2026-04-15 15:30'),
(4, 4, 3,    'Red wrap midi dress, S',                       30.00, 'Completed',        '2026-04-10 09:12', '2026-04-15 15:30'),
(5, 4, 3,    'Bridesmaid dress, lavender (brought in)',      30.00, 'Completed',        '2026-05-03 10:30', '2026-05-09 13:00'),
(2, 1, 2,    'Black tailored trousers, 34x32',               15.00, 'Completed',        '2026-06-12 15:05', '2026-06-16 11:00'),
(2, 2, 4,    'Black tailored trousers, 34x32',               20.00, 'Completed',        '2026-06-12 15:05', '2026-06-16 11:00'),
(3, 4, 3,    'Little black dress, M',                        30.00, 'Completed',        '2026-08-19 17:45', '2026-08-24 14:00'),
(1, 5, 2,    'Charcoal two-piece suit jacket, 40R',          60.00, 'Ready for Pickup', '2026-09-08 10:06', NULL),
(7, 2, 4,    'Tailored trousers, 34x32',                     20.00, 'In Progress',      '2026-10-02 11:15', NULL),
(7, 1, 4,    'Tailored trousers, 34x32',                     15.00, 'In Progress',      '2026-10-02 11:15', NULL),
(8, 3, NULL, 'Leather jacket, M (brought in)',               25.00, 'Received',         '2026-10-28 16:20', NULL),
(4, 3, NULL, 'Navy wool blend blazer, L',                    25.00, 'Received',         '2026-10-25 14:30', NULL);

-- Recalculate OrderAmount from the items so totals are always consistent.
-- (Alteration fees are billed on the AlterationOrder, not on a sales order.)
UPDATE Orders o
SET OrderAmount =
      COALESCE((SELECT SUM(oi.Quantity * oi.UnitPrice) FROM OrderItem oi WHERE oi.OrderID = o.OrderID), 0)
WHERE o.OrderID > 0;   -- key-based WHERE keeps MySQL Workbench "safe update" mode happy

-- Payments: one per order. Amount matches the order total above.
-- Card payments store only the last 4 digits of the card.
INSERT INTO Payment (OrderID, PaymentMethod, CardLastFour, Amount, PaymentDate) VALUES
( 1, 'Credit Card', '4242', 129.97, '2026-02-03 10:16'),
( 2, 'Credit Card', '1881', 299.99, '2026-02-14 14:03'),
( 3, 'Debit Card',  '5310', 179.98, '2026-03-05 11:31'),
( 4, 'Credit Card', '4242', 139.97, '2026-03-22 16:46'),
( 5, 'Cash',        NULL,   309.97, '2026-04-10 09:06'),
( 6, 'Gift Card',   NULL,    84.98, '2026-05-01 13:21'),
( 7, 'Credit Card', '1881', 184.97, '2026-06-12 15:01'),
( 8, 'Debit Card',  '7720',  89.98, '2026-07-04 12:11'),
( 9, 'Debit Card',  '5310', 259.97, '2026-08-19 17:41'),
(10, 'Credit Card', '4242', 384.97, '2026-09-08 10:01'),
(11, 'Cash',        NULL,   104.98, '2026-10-02 11:12'),
(12, 'Credit Card', '9034', 149.99, '2026-10-25 14:31');
