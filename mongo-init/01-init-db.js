// MongoDB Initialization Script for WM-MEGA
// This script runs when MongoDB container starts for the first time

// Switch to walmart database
db = db.getSiblingDB('walmart');

// Create application user with read/write permissions
db.createUser({
  user: 'wm_mega_user',
  pwd: 'wm_mega',
  roles: [
    {
      role: 'readWrite',
      db: 'walmart'
    }
  ]
});

// Create initial collections with indexes
db.createCollection('products');
db.createCollection('logs');
db.createCollection('batch_ids');
db.createCollection('generated_skus');
db.createCollection('trademark_ids');

// Create indexes for better performance
db.products.createIndex({ "name": 1 });
db.products.createIndex({ "link": 1 });
db.products.createIndex({ "sku": 1 });
db.products.createIndex({ "timestamp": -1 });

db.logs.createIndex({ "timestamp": -1 });
db.logs.createIndex({ "department": 1 });
db.logs.createIndex({ "status": 1 });

db.batch_ids.createIndex({ "batch_id": 1 }, { unique: true });
db.generated_skus.createIndex({ "sku": 1 }, { unique: true });

// Insert initial trademark data structure
db.trademark_ids.insertOne({
  "trademarks": [],
  "entities": [],
  "created_at": new Date(),
  "updated_at": new Date()
});

print('WM-MEGA MongoDB initialization completed successfully!');
print('Database: walmart');
print('User: wm_mega_user');
print('Collections created: products, logs, batch_ids, generated_skus, trademark_ids');
