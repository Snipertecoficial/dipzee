// Creates a scoped application user (readWrite on the app database ONLY) so
// the backend never has to connect using the cluster root/admin account.
//
// Runs automatically via docker-entrypoint-initdb.d — but only the FIRST
// time a container starts against a genuinely empty /data/db volume (this is
// how the official mongo image's init mechanism works). It will not run
// again on an already-initialized volume; if you need to (re)create this
// user against an existing volume, run the equivalent createUser command by
// hand with mongosh instead.
const dbName = process.env.MONGO_APP_DB;
const appUser = process.env.MONGO_APP_USER;
const appPassword = process.env.MONGO_APP_PASSWORD;

if (!dbName || !appUser || !appPassword) {
  print('init-app-user.js: MONGO_APP_DB/MONGO_APP_USER/MONGO_APP_PASSWORD not set — skipping scoped user creation.');
} else {
  const targetDb = db.getSiblingDB(dbName);
  targetDb.createUser({
    user: appUser,
    pwd: appPassword,
    roles: [{ role: 'readWrite', db: dbName }],
  });
  print(`init-app-user.js: created scoped user '${appUser}' with readWrite on '${dbName}' only.`);
}
