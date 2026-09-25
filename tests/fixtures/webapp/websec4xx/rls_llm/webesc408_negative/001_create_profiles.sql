CREATE TABLE profiles (
    id uuid PRIMARY KEY,
    user_id uuid REFERENCES auth.users
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
