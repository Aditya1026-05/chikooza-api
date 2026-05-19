import {
  createContext,
  forwardRef,
  useContext,
  useMemo,
  useState,
} from "react";

const DropdownContext = createContext(null);

const cx = (...classes) =>
  classes
    .flatMap((value) => (typeof value === "string" ? value.split(" ") : value))
    .filter(Boolean)
    .join(" ");

const colClass = (breakpoint, value) => {
  if (value == null || value === false) {
    return "";
  }

  const prefix = breakpoint ? `${breakpoint}-` : "";
  if (value === true) {
    return breakpoint ? `col-${breakpoint}` : "col";
  }

  if (typeof value === "object") {
    return cx(
      value.size ? `col-${prefix}${value.size}` : "",
      value.offset ? `offset-${prefix}${value.offset}` : "",
      value.order ? `order-${prefix}${value.order}` : "",
    );
  }

  return value === "auto" ? `col-${prefix}auto` : `col-${prefix}${value}`;
};

const passthrough = (Component, baseClass) =>
  forwardRef(({ className, ...props }, ref) => (
    <Component ref={ref} className={cx(baseClass, className)} {...props} />
  ));

// U: OLD: reactstrap wrapped Bootstrap components but carries a React 18-only react-popper peer.
// U: NEW: keep the existing reactstrap import surface with small Bootstrap 5 wrappers.
export const Container = forwardRef(({ fluid, className, ...props }, ref) => (
  <div
    ref={ref}
    className={cx(fluid ? "container-fluid" : "container", className)}
    {...props}
  />
));

export const Row = passthrough("div", "row");

export const Col = forwardRef(
  ({ xs, sm, md, lg, xl, xxl, className, ...props }, ref) => {
    const classes = cx(
      colClass("", xs),
      colClass("sm", sm),
      colClass("md", md),
      colClass("lg", lg),
      colClass("xl", xl),
      colClass("xxl", xxl),
      !xs && !sm && !md && !lg && !xl && !xxl ? "col" : "",
      className,
    );

    return <div ref={ref} className={classes} {...props} />;
  },
);

export const Card = passthrough("div", "card");
export const CardBody = passthrough("div", "card-body");
export const CardHeader = passthrough("div", "card-header");
export const CardText = passthrough("p", "card-text");

export const CardTitle = forwardRef(
  ({ tag: Tag = "div", className, ...props }, ref) => (
    <Tag ref={ref} className={cx("card-title", className)} {...props} />
  ),
);

export const CardSubtitle = forwardRef(
  ({ tag: Tag = "div", className, ...props }, ref) => (
    <Tag ref={ref} className={cx("card-subtitle", className)} {...props} />
  ),
);

export const CardImg = forwardRef(
  ({ bottom, className, ...props }, ref) => (
    <img
      ref={ref}
      className={cx(bottom ? "card-img-bottom" : "card-img-top", className)}
      {...props}
    />
  ),
);

export const Table = passthrough("table", "table");
export const Form = passthrough("form", "");
export const FormGroup = passthrough("div", "mb-3");
export const FormText = passthrough("div", "form-text");

export const Label = forwardRef(({ for: htmlFor, className, ...props }, ref) => (
  <label
    ref={ref}
    htmlFor={htmlFor}
    className={cx("form-label", className)}
    {...props}
  />
));

export const Input = forwardRef(
  ({ type = "text", className, children, ...props }, ref) => {
    if (type === "select") {
      return (
        <select ref={ref} className={cx("form-select", className)} {...props}>
          {children}
        </select>
      );
    }

    if (type === "textarea") {
      return (
        <textarea ref={ref} className={cx("form-control", className)} {...props}>
          {children}
        </textarea>
      );
    }

    return (
      <input
        ref={ref}
        type={type}
        className={cx(type === "checkbox" ? "form-check-input" : "form-control", className)}
        {...props}
      />
    );
  },
);

export const Button = forwardRef(
  (
    {
      color = "secondary",
      outline,
      size,
      className,
      tag: Tag = "button",
      type,
      ...props
    },
    ref,
  ) => {
    const colorClass =
      color === "transparent"
        ? "btn-transparent"
        : `btn${outline ? "-outline" : ""}-${color}`;

    return (
      <Tag
        ref={ref}
        type={Tag === "button" ? type || "button" : type}
        className={cx("btn", colorClass, size ? `btn-${size}` : "", className)}
        {...props}
      />
    );
  },
);

export const Alert = forwardRef(
  ({ color = "primary", className, ...props }, ref) => (
    <div
      ref={ref}
      role="alert"
      className={cx("alert", `alert-${color}`, className)}
      {...props}
    />
  ),
);

export const Spinner = forwardRef(
  ({ color, size, className, children, ...props }, ref) => (
    <span
      ref={ref}
      role="status"
      className={cx(
        "spinner-border",
        color ? `text-${color}` : "",
        size ? `spinner-border-${size}` : "",
        className,
      )}
      {...props}
    >
      {children}
    </span>
  ),
);

export const Breadcrumb = forwardRef(({ className, ...props }, ref) => (
  <ol ref={ref} className={cx("breadcrumb", className)} {...props} />
));

export const BreadcrumbItem = forwardRef(
  ({ active, className, ...props }, ref) => (
    <li
      ref={ref}
      className={cx("breadcrumb-item", active ? "active" : "", className)}
      aria-current={active ? "page" : undefined}
      {...props}
    />
  ),
);

export const ListGroup = forwardRef(({ flush, className, ...props }, ref) => (
  <ul
    ref={ref}
    className={cx("list-group", flush ? "list-group-flush" : "", className)}
    {...props}
  />
));

export const ListGroupItem = forwardRef(
  ({ action, tag: Tag = "li", className, ...props }, ref) => (
    <Tag
      ref={ref}
      className={cx("list-group-item", action ? "list-group-item-action" : "", className)}
      {...props}
    />
  ),
);

export const Navbar = forwardRef(
  ({ light, dark, expand, className, ...props }, ref) => {
    const expandClass =
      expand === true ? "navbar-expand" : expand ? `navbar-expand-${expand}` : "";

    return (
      <nav
        ref={ref}
        className={cx(
          "navbar",
          expandClass,
          dark ? "navbar-dark" : light ? "navbar-light" : "",
          className,
        )}
        {...props}
      />
    );
  },
);

export const NavbarBrand = passthrough("a", "navbar-brand");

export const Collapse = forwardRef(
  ({ navbar, isOpen, className, ...props }, ref) => (
    <div
      ref={ref}
      className={cx(navbar ? "collapse navbar-collapse" : "collapse", isOpen ? "show" : "", className)}
      {...props}
    />
  ),
);

export const Nav = forwardRef(({ navbar, className, ...props }, ref) => (
  <ul ref={ref} className={cx(navbar ? "navbar-nav" : "nav", className)} {...props} />
));

export const NavItem = passthrough("li", "nav-item");

export const Dropdown = forwardRef(
  ({ isOpen, toggle, className, children, ...props }, ref) => {
    const [internalOpen, setInternalOpen] = useState(false);
    const open = typeof isOpen === "boolean" ? isOpen : internalOpen;
    const value = useMemo(
      () => ({
        open,
        toggle: toggle || (() => setInternalOpen((current) => !current)),
      }),
      [open, toggle],
    );

    return (
      <DropdownContext.Provider value={value}>
        <div
          ref={ref}
          className={cx("dropdown", open ? "show" : "", className)}
          {...props}
        >
          {children}
        </div>
      </DropdownContext.Provider>
    );
  },
);

export const UncontrolledDropdown = forwardRef(
  ({ nav, inNavbar, className, ...props }, ref) => (
    <Dropdown ref={ref} className={cx(nav ? "nav-item" : "", className)} {...props} />
  ),
);

export const DropdownToggle = forwardRef(
  (
    {
      caret,
      nav,
      color = "secondary",
      className,
      tag: Tag = "button",
      onClick,
      type,
      ...props
    },
    ref,
  ) => {
    const context = useContext(DropdownContext);
    const colorClass = color === "transparent" ? "btn-transparent" : `btn-${color}`;

    return (
      <Tag
        ref={ref}
        type={Tag === "button" ? type || "button" : type}
        className={cx(nav ? "nav-link" : "btn", !nav ? colorClass : "", caret ? "dropdown-toggle" : "", className)}
        aria-expanded={context?.open}
        onClick={(event) => {
          onClick?.(event);
          context?.toggle?.(event);
        }}
        {...props}
      />
    );
  },
);

export const DropdownMenu = forwardRef(
  ({ end, right, className, ...props }, ref) => {
    const context = useContext(DropdownContext);

    return (
      <div
        ref={ref}
        className={cx(
          "dropdown-menu",
          end || right ? "dropdown-menu-end" : "",
          context?.open ? "show" : "",
          className,
        )}
        {...props}
      />
    );
  },
);

export const DropdownItem = forwardRef(
  ({ className, onClick, ...props }, ref) => {
    const context = useContext(DropdownContext);

    return (
      <div
        ref={ref}
        role="menuitem"
        tabIndex={0}
        className={cx("dropdown-item", className)}
        onClick={(event) => {
          onClick?.(event);
          context?.toggle?.(event);
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onClick?.(event);
            context?.toggle?.(event);
          }
        }}
        {...props}
      />
    );
  },
);
