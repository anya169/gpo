const Header = ({ logo, navigation, user, className = "" }) => {
   return (
      <nav className={`navbar navbar-expand-lg navbar-light bg-light ${className}`}>
      <Container>
         <a className="navbar-brand" href="#">
            {logo || "Logo"}
         </a>

         <div className="collapse navbar-collapse" id="navbarNav">
            <ul className="navbar-nav me-auto">
            {navigation?.map((item) => (
               <li key={item.name} className="nav-item">
                  <a className="nav-link" href={item.href}>
                  {item.name}
                  </a>
               </li>
            ))}
            </ul>
            
            <div className="d-flex">
               {user || <Button variant="outline-primary">Войти</Button>}
            </div>
         </div>
      </Container>
      </nav>
   );
};

export default Header;