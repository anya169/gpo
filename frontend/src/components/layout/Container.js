const Container = ({ children, className = "", fluid = false }) => {
   return (
      <div className={`${fluid ? 'container-fluid' : 'container'} ${className} d-flex flex-column`}>
      {children}
      </div>
   );
};

export default Container;