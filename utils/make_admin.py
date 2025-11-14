from argon2 import PasswordHasher

# Generate a simple password for the administrator account for local deployment.
# argon2 password hasher with optimal settings
pwdHash = PasswordHasher(memory_cost=64, time_cost=3, parallelism=1 )
print(pwdHash.hash("admin::admin123"))