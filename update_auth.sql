-- Update ATS schema to support password authentication without data loss.
-- Default hash corresponds to password: Password@123

ALTER TABLE Candidates
ADD COLUMN password_hash VARCHAR(255) NOT NULL
DEFAULT 'scrypt:32768:8:1$10KH8IRS56WBMbea$6fc66f858dda175196783d3a156461fadc7b0207715437740066739c48eb463656703ac74e48b3d7da288f18f4be04f04d7b4ac0d6815a5bbf42db85dccd5f2e';

ALTER TABLE Recruiters
ADD COLUMN password_hash VARCHAR(255) NOT NULL
DEFAULT 'scrypt:32768:8:1$10KH8IRS56WBMbea$6fc66f858dda175196783d3a156461fadc7b0207715437740066739c48eb463656703ac74e48b3d7da288f18f4be04f04d7b4ac0d6815a5bbf42db85dccd5f2e';
