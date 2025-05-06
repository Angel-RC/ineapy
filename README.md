# INEapy

INEapy is a comprehensive Python library designed to provide seamless access to data from the Spanish National Statistics Institute (INE). The library is structured into two primary modules: `ine_wrapper` and `ine_consultor`, each serving distinct purposes to cater to different user needs.

If you want to access to the API's details, you can check it's [documentation](https://www.ine.es/dyngs/DAB/index.htm?cid=1099).

## Installation

To install INEapy, simply run the following command:

```bash
pip install ineapy
```

## Overview

INEapy offers a robust interface for interacting with the INE's extensive data offerings. Whether you need low-level access to the API or a more abstracted, user-friendly interface, INEapy has you covered.

## Modules

### INEWrapper

The `ine_wrapper` module provides a direct and low-level interface with the INE API, allowing users to perform HTTP requests to various endpoints with precision and control.

#### Key Features:
- Comprehensive access to all available operations in the INE API
- Rigorous parameter validation to ensure data integrity
- Efficient pagination handling for large datasets
- Multi-language support (ES/EN) for broader accessibility

#### Initialization:
```python
from ineapy import INEWrapper

# Initialize the wrapper (default in Spanish)
wrapper = INEWrapper()

# Initialize the wrapper in English
wrapper_en = INEWrapper(language="EN")
```

#### Core Methods:

- `get_operacion(cod_operation, det, tip)`: Retrieve detailed information about a statistical operation.
- `get_operaciones_disponibles(det, tip, geo)`: Access the list of available operations.
- `get_publicaciones_operacion(cod_operation, det, tip)`: Fetch publications associated with a specific operation.
- `get_variables()`: Access the complete list of variables available in the system.
- `get_variables_operacion(cod_operation, det, tip)`: Retrieve variables associated with a specific operation.
- `get_valores_variable(id_variable, det, tip)`: Obtain possible values for a given variable.
- `get_serie(cod_serie, det, tip)`: Access information about a specific series.
- `get_datos_serie(cod_serie, nult, date, det, tip)`: Retrieve data from a specific series.
- `get_datos_metadata_operacion(cod_operation, filters, p, det, tip, nult, date)`: Fetch data with metadata for an operation.
- `get_tablas_operacion(cod_operation, det, tip)`: Access tables associated with a specific operation.
- `get_grupos_tabla(id_table, det, tip)`: Retrieve groups of a table.
- `get_valores_grupos_tabla(id_table, id_grupo, det, tip)`: Obtain values of a table group.
- `get_datos_tabla(id_table, nult, date, det, tip, filters)`: Retrieve data from a specific table.

#### Common Parameters:
- `det`: Detail level (0, 1, or 2)
- `tip`: Response type ("", "A", "M", "AM")
  - "": Normal response
  - "A": Friendly response
  - "M": Includes metadata
  - "AM": Friendly with metadata
- `nult`: Number of latest data points to retrieve
- `date`: Date filter in the format "yyyymmdd:yyyymmdd"
- `filters`: List of filters in the format "id_variable:id_value"

#### Usage Example:
```python
from ineapy import INEWrapper

# Initialize the wrapper
wrapper = INEWrapper()

# List available operations
response = wrapper.get_operaciones_disponibles(det=0, tip="")
operations = response.json()

# Get information about an operation
response = wrapper.get_operacion("IPC", det=0, tip="M")
data = response.json()

# Get data from a series
response = wrapper.get_datos_serie("IPC277517", nult=12)
series_data = response.json()
```

### INEConsultor

The `ine_consultor` module offers a high-level abstraction over `ine_wrapper`, simplifying access to INE data and enhancing data manipulation capabilities.

#### Key Features:
- Simplified interface for streamlined data access
- Automatic conversion of responses to more manageable formats
- Comprehensive methods for listing and querying operations, variables, and series

#### Initialization:
```python
from ineapy import INEConsultor

# Initialize the consultant (default in Spanish)
consultor = INEConsultor()

# Initialize the consultant in English
consultor_en = INEConsultor(language="EN")
```

#### Core Methods:

- `list_operations(filter_geo)`: List available operations.
- `get_info_operation(cod_operation)`: Retrieve information about a specific operation.
- `list_variables(cod_operation)`: List available variables, either general or specific to an operation.
- `list_periodicities()`: List available periodicities.
- `list_filters_from_variable(id_variable)`: List values for a specific variable.
- `list_filters_from_variable_operation(cod_operation, id_variable)`: List values for a variable within an operation.
- `get_info_serie(cod_serie)`: Retrieve detailed information about a series.
- `get_data_serie(cod_serie, nult, date)`: Access data from a specific series.
- `get_data_operation(cod_operation, filters, p, date, nult)`: Retrieve data from an operation with specified filters.
- `list_groups_from_table(id_table)`: List groups within a table.
- `list_filters_from_table(id_table)`: List available filters for a table.
- `get_data_table(id_table, nult, date, filters)`: Access data from a specific table.

#### Usage Example:
```python
from ineapy import INEConsultor
import pandas as pd

# Initialize the consultant
consultor = INEConsultor()

# List available operations
operations = consultor.list_operations()

# Get information about the IPC operation
operation_info = consultor.get_info_operation("IPC")

# List variables for an operation
variables = consultor.list_variables("IPC")

# Get data from a series with the last 12 values
data = consultor.get_data_serie("IPC277517", nult=12)

# Convert to pandas DataFrame
df = pd.DataFrame(data)
```

## Data Structure

Responses from `INEConsultor` are consistently returned in simplified formats, typically as lists of dictionaries or dictionaries. Dates are automatically converted to pandas `datetime` objects to facilitate analysis.

## Contribution
Contributions to INEapy are highly encouraged. To contribute, please:
1. Fork the repository
2. Create a branch for your feature
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

By following these steps, you can help enhance the functionality and usability of INEapy for the community.
