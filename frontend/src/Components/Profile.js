function Profile({ user }) {
  return (
    <div className="card form-card">
      <h2>👤 Profile</h2>
      <p><b>Name:</b> {user.fullname}</p>
      <p><b>Email:</b> {user.email}</p>
      <p><b>Phone:</b> {user.phone}</p>
    </div>
  );
}

export default Profile;
