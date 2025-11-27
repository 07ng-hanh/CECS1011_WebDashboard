# TO-DOs
- [User/Warehouse] Show quantity of all produces
- [User/Warehouse] Show warnings and push notification if quantity exceed storage capacity
- [User/Sensors] Show latest temperature, CO2 concentration and humidity
- [User/Warehouse] Look-up and sort batches by:
  - Produce Name
  - Produce ID
  - Batch ID
  - Weight
  - Quantity
  - Import Date (range)
  - Date Remaining before EXP (range)
  - Status (Pending, Assigned Order, Discarded)
- [User/Warehouse] List all near-expiration produces
- [User/Warehouse] Get a batch's info as stored in DB (including finalized shipping destination)
- [User/Sensors] Warning if safety threshold (user-defined or smallest range for any batch, whichever lower) (red flash OR push notification)
- [User/Sensors] Historical view of temperature, CO2 concentration and humidity
- [User/Warehouse] Show batches exceeding one or more thresholds
- [User/Order] Show orders and their statuses
- [User/Order] Add new order
- [User/Order] Delete order + Remove order ID from its target batches
- [User/Order] Finalize order
- [User/Order] Fulfill order
- [Admin/Users] Create, list and delete new user
- [Admin/Users] Grant and revoke an user admin rights
- [Admin/Produce] Add, delete and update new produce
- [Admin/Warehouse] Manually trigger purging sold or discarded produces

### Deferred

- [User/Order] Suggest batches for fulfillment for pending orders.
- [User/Order] Build a suggestion table
  - Row: Order_ID, List of Batch_IDs
  - On order newly added:
    - Check all available batches of the matching Produce_ID
    - Call AI to do optimization
    - For each Order_ID: update list of Batch_IDs if needed
    - Add new Order_ID
  - On order removed:
    - Remove order entry from suggestion table
  - On order updated:
    - Update table as in newly added


### Less important
- [User/Warehouse] Export QR Code for one or many produces

