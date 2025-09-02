use pyo3::prelude::*;
use regex::Regex;

/// Compile a Haske path into a regex string with named captures.
/// Example: "/user/:id" -> r"^/user/(?P<id>[^/]+)$"
#[pyfunction]
pub fn compile_path(path: &str) -> PyResult<String> {
    if !path.starts_with('/') {
        return Err(pyo3::exceptions::PyValueError::new_err("path must start with /"));
    }
    
    // Validate path doesn't contain invalid patterns
    if path.contains("::") || path.contains("//") {
        return Err(pyo3::exceptions::PyValueError::new_err("path contains invalid pattern"));
    }
    
    let mut out = String::new();
    out.push('^');
    let mut chars = path.chars().peekable();
    let mut param_count = 0;
    
    while let Some(c) = chars.next() {
        if c == ':' {
            let mut name = String::new();
            while let Some(&ch) = chars.peek() {
                if ch.is_alphanumeric() || ch == '_' {
                    name.push(ch);
                    chars.next();
                } else {
                    break;
                }
            }
            if name.is_empty() {
                return Err(pyo3::exceptions::PyValueError::new_err("empty param name"));
            }
            param_count += 1;
            if param_count > 20 {
                return Err(pyo3::exceptions::PyValueError::new_err("too many parameters in path (max 20)"));
            }
            out.push_str(&format!("(?P<{}>[^/]+)", name));
        } else {
            match c {
                '.'|'+'|'*'|'?'|'(' | ')' | '[' | ']' | '{' | '}' | '|' | '^' | '$' | '\\' => {
                    out.push('\\'); out.push(c);
                }
                other => out.push(other),
            }
        }
    }
    out.push('$');
    
    // Validate the regex compiles correctly
    Regex::new(&out)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("invalid regex generated: {}", e)))?;
    
    Ok(out)
}

/// Validate if a path matches a pattern and extract parameters
#[pyfunction]
pub fn match_path(pattern: &str, path: &str) -> PyResult<Option<Vec<(String, String)>>> {
    let regex = Regex::new(pattern)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("invalid regex pattern: {}", e)))?;
    
    if let Some(caps) = regex.captures(path) {
        let mut params = Vec::new();
        for name in regex.capture_names().flatten() {
            if let Some(m) = caps.name(name) {
                params.push((name.to_string(), m.as_str().to_string()));
            }
        }
        Ok(Some(params))
    } else {
        Ok(None)
    }
}