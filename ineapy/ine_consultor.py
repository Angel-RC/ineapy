from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from ineapy.ine_wrapper import INEWrapper


class INEConsultor:
    """
    Main class for querying data from the National Statistics Institute (INE) of Spain.

    This class provides a high-level interface to access and query statistical data
    from the INE using the INEWrapper. It allows performing operations such as:
    - Listing available operations, variables and periodicities
    - Getting detailed information about operations, tables and series
    - Querying statistical data with different filters and parameters
    - Getting metadata associated with series and operations

    Args:
        language (str, optional): Language for responses. Default is "ES" (Spanish).

    Attributes:
        client (INEWrapper): Client for making requests to the INE API
        periodicities (dict): Dictionary with available periodicities
        variables (dict): Dictionary with available variables
    """

    def __init__(self, language: str = "ES"):
        self.client = INEWrapper(language)
        periodicities = self.list_periodicities()
        self.periodicities = {item["id"]: item["name"] for item in periodicities}
        self.variables = {item["id_variable"]: item["name_variable"] for item in self.list_variables()}

    def __get_data_from_response(self, response, void_response={}):
        if not response.ok:
            raise Exception(
                f"Error code {response.status_code}: {response.reason} when requesting {response.url}. Please check the url and validate the parameters."
            )
        return response.json() if response.content else void_response

    def list_periodicities(self) -> Dict[str, Any]:
        """
        Retrieves a list of periodicities from the INE.

        Returns:
            list: A list of dictionaries, where each dictionary contains:
                - 'id' (int): The ID of the periodicity.
                - 'nombre' (str): The name of the periodicity.
        """
        response = self.client.get_periodicidades()
        data = self.__get_data_from_response(response)
        data = [{"id": periodicity["Id"], "name": periodicity["Nombre"]} for periodicity in data]
        return data

    def list_filters_from_variable_operation(self, cod_operation: str, id_variable: str) -> Dict[str, Any]:
        """
        Retrieves a list of values associated with a specific variable and operation.

        Args:
            id_variable (str, optional): The ID of the variable to query.
            id_operation (int, optional): The ID of the operation to query.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary contains:
            - "id_valor" (str): The ID of the value.
            - "nombre_valor" (str): The name of the value.
        """
        response = self.client.get_valores_variable_operacion(id_variable, cod_operation, det=1, tip="A")
        data = self.__get_data_from_response(response)
        data = [
            {
                "id_variable": valor["Variable"].get("Id"),
                "name_variable": valor["Variable"].get("Nombre"),
                "id_value": valor["Id"],
                "name_value": valor["Nombre"],
            }
            for valor in data
        ]
        return data

    def list_tables_from_operation(self, cod_operation: str) -> List:
        """
        Retrieves a list of tables associated with a specific operation ID.

        This method sends a GET request to the endpoint `/TABLAS_OPERACION/{cod_operation}`
        with specific query parameters and processes the response to extract relevant
        information about the tables.

        Args:
            cod_operation (str): The ID of the operation to retrieve tables for.

        Returns:
            list[dict]: A list of dictionaries, where each dictionary contains the information of the tables.
        """
        info_operation = self.get_info_operation(cod_operation=cod_operation)

        response_tables = self.client.get_tablas_operacion(cod_operation, det=1, tip="")
        data = self.__get_data_from_response(response_tables)

        data = [
            info_operation
            | {
                "id_table": table["Id"],
                "cod_table": table["Codigo"],
                "name_table": table["Nombre"],
                "periodicity": table["Periodicidad"].get("Nombre"),
                "publication": table["Publicacion"].get("Nombre"),
                "year_start": table["Anyo_Periodo_ini"],
                "updated_at": pd.to_datetime(table["Ultima_Modificacion"], unit="ms"),
            }
            for table in data
        ]
        return data

    def list_filters_from_operation(self, id_operation: str):
        """
        Retrieves and processes a list of filters (variables and their values)
        associated with a specific operation.

        Args:
            id_operation (str): The ID of the operation for which to retrieve filters.

        Returns:
            list[dict]: A list of dictionaries, where each dictionary represents a
            variable-value pair with the following keys:
                - "id_variable" (str): The ID of the variable.
                - "nombre_variable" (str): The name of the variable.
                - "id_valor" (str): The ID of the value.
                - "nombre_valor" (str): The name of the value.

        """
        response = self.client.get_variables_operacion(id_operation, det=2, tip="A")
        variables = self.__get_data_from_response(response)
        variables = [
            {
                "id_variable": variable["Id"],
                "name_variable": variable["Nombre"],
                "id_value": value["Id"],
                "name_value": value["Nombre"],
            }
            for variable in variables
            for value in variable["Valores"]
        ]
        return variables

    def get_info_operation(self, cod_operation: str):
        """
        Retrieves information about a specific operation by its ID.

        Args:
            id_operation (str): The unique identifier of the operation.

        Returns:
            dict: A dictionary containing the operation's details with the following keys:
                - "id_operation" (str): The ID of the operation.
                - "cod_operacion" (str): The code of the operation.
                - "nombre_operacion" (str): The name of the operation.
        """
        response = self.client.get_operacion(cod_operation, det=0, tip="M")
        data = self.__get_data_from_response(response, {})
        data = {"id_operation": data["Id"], "cod_operation": data["Codigo"], "name_operation": data["Nombre"]}
        return data

    def list_series_from_operation(self, cod_operation: str, p: str = None, filters: List[str] = []) -> List:
        """
        Retrieves a list of series for a specific operation.
        Parameters:
            cod_operation (str): The identifier of the operation.
            p (int): The periodicity of the data.
            filters (str): Filters to apply to the data query, formatted as strings with format 'id_variable:id_value' or 'id_variable:'.
        Returns:
            list: A list with the series's info.
        """

        if len(filters) > 0:
            response_series = self.client.get_serie_metadata_operacion_all_pages(
                cod_operation=cod_operation, det=0, tip="M", filters=filters, p=p
            )
        else:
            response_series = self.client.get_series_operacion_all_pages(cod_operation=cod_operation, det=0, tip="M")

        response_series = [self.__get_data_from_response(response) for response in response_series]
        series = sum(response_series, [])
        if p:
            series = [serie for serie in series if serie["FK_Periodicidad"] == p]

        series = [
            {
                "id_serie": serie["Id"],
                "cod_serie": serie["COD"],
                "name_serie": serie["Nombre"],
                "periodicity": self.periodicities[serie["FK_Periodicidad"]],
                "metadata": [
                    {
                        "id_variable": metadata["FK_Variable"],
                        "name_variable": self.variables[metadata["FK_Variable"]],
                        "id_value": metadata["Id"],
                        "name_value": metadata["Nombre"],
                    }
                    for metadata in serie["MetaData"]
                ],
            }
            for serie in series
        ]
        return series

    def list_groups_from_table(self, id_table: str):
        """
        Retrieves a list of groups from a specified table.

        Args:
            id_table (str): The ID of the table to retrieve groups from.

        Returns:
            list: A list of dictionaries, where each dictionary contains:
                - "id_grupo" (str): The ID of the group.
                - "nombre_grupo" (str): The name of the group.
        """
        response = self.client.get_grupos_tabla(id_table, det=2, tip="M")
        data = self.__get_data_from_response(response)
        data = [{"id_group": grupo["Id"], "name_group": grupo["Nombre"]} for grupo in data]
        return data

    def list_filters_from_table(self, id_table: str):
        """
        Retrieves and processes a list of filters from a specified table.
        Args:
            id_table (str): The ID of the table to retrieve filters from.
        Returns:
            list: A list of dictionaries, where each dictionary contains possible filters for the table.
        """
        groups = self.list_groups_from_table(id_table)
        data = []
        for group in groups:
            response = self.client.get_valores_grupos_tabla(id_table, str(group["id_group"]), det=1, tip="A")
            values_group = self.__get_data_from_response(response)
            data += [
                group
                | {
                    "id_variable": value["Variable"].get("Id"),
                    "name_variable": value["Variable"].get("Nombre"),
                    "id_value": value.get("Id"),
                    "name_value": value["Nombre"],
                }
                for value in values_group
            ]
        return data

    def list_series_from_table(self, id_table: str):
        """
        Retrieves and processes a list of series from a specified table.

        Args:
            id_table (str): The ID of the table to retrieve series from.

        Returns:
            list: A list of processed series information, where each series is cleaned using
                  the `__clean_serie_info` method.
        """
        response = self.client.get_series_tabla(id_table, det=0, tip="M")
        data = self.__get_data_from_response(response)
        data = [
            {
                "id_serie": serie["Id"],
                "cod_serie": serie["COD"],
                "name_serie": serie["Nombre"],
                "periodicity": self.periodicities[serie["FK_Periodicidad"]],
                "metadata": [
                    {
                        "id_variable": metadata["FK_Variable"],
                        "name_variable": self.variables[metadata["FK_Variable"]],
                        "id_value": metadata["Id"],
                        "name_value": metadata["Nombre"],
                    }
                    for metadata in serie["MetaData"]
                ],
            }
            for serie in data
        ]
        return data

    def get_info_serie(self, cod_serie: str):
        """
        Retrieves and processes information for a specific series by its ID.

        Args:
            id_serie (str): The unique identifier of the series.

        Returns:
            dict: A dictionary containing the cleaned and processed series information.
        """
        response = self.client.get_serie(cod_serie, det=1, tip="M")
        data = self.__get_data_from_response(response)
        data = {
            "id_serie": data["Id"],
            "cod_serie": data["COD"],
            "name_serie": data["Nombre"],
            "periodicity": data["Periodicidad"].get("Nombre"),
            "publication": data["Publicacion"].get("Nombre"),
            "clasification": data["Clasificacion"].get("Nombre"),
            "unidad": data["Unidad"].get("Nombre"),
            "metadata": [
                {
                    "id_variable": metadata["FK_Variable"],
                    "name_variable": self.variables[metadata["FK_Variable"]],
                    "id_value": metadata["Id"],
                    "name_value": metadata["Nombre"],
                }
                for metadata in data["MetaData"]
            ],
        }

        return data

    def list_variables(self, cod_operation: str = None) -> List[Dict[str, Any]]:
        """
        Retrieves a list of available variables from the INE.

        This method can either retrieve all available variables or limit the results
        to variables associated with a specific operation.

        Args:
            cod_operation (str, optional): Code of the operation to retrieve variables for.
                                         If None, retrieves all available variables.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary contains:
                - "id_variable" (str): The ID of the variable.
                - "name_variable" (str): The name of the variable.
        """
        if cod_operation:
            response = self.client.get_variables_operacion(cod_operation, det=0, tip="")
        else:
            response = self.client.get_variables(det=0, tip="")
        data = self.__get_data_from_response(response)
        data = [{"id_variable": variable["Id"], "name_variable": variable["Nombre"]} for variable in data]
        return data

    def list_operations(self, filter_geo: int = None):
        """
        Retrieves a list of available operations.

        This method sends a GET request to the "/OPERACIONES_DISPONIBLES" endpoint and processes the response to extract
        relevant information about each operation.

        Args:
            filter_geo (int): 0 if you want national results or 1 if you want results by autonomous communities, provinces, municipalities, and other disaggregations

        Returns:
            list[dict]: A list of dictionaries, where each dictionary contains:
                - 'id_operation' (int): The ID of the operation.
                - 'name_operation' (str): The name of the operation.
                - 'cod_operation' (str): The code of the operation.
        """
        response = self.client.get_operaciones_disponibles(det=0, tip="", geo=filter_geo)
        data = self.__get_data_from_response(response)
        data = [
            {
                "id_operation": operation["Id"],
                "name_operation": operation["Nombre"],
                "cod_operation": operation["Codigo"],
            }
            for operation in data
        ]
        return data

    def list_filters_from_variable(self, id_variable: str):
        """
        Retrieves a list of values associated with a specific variable ID.

        Args:
            id_variable (str): The ID of the variable for which to retrieve values.

        Returns:
            list: A list of dictionaries, where each dictionary contains:
                - "id_value" (str): The ID of the value.
                - "name_value" (str): The name of the value.
        """
        response = self.client.get_valores_variable(id_variable, det=1, tip="M")
        data = self.__get_data_from_response(response)
        data = [
            {
                "id_variable": valor["Variable"].get("Id"),
                "name_variable": valor["Variable"].get("Nombre"),
                "id_value": valor["Id"],
                "name_value": valor["Nombre"],
            }
            for valor in data
        ]
        return data

    def get_metadata_serie(self, cod_serie: str):
        """
        Retrieves metadata from a specific serie by its ID.

        Args:
            cod_serie (str): The ID of the series to retrieve metadata for.

        Returns:
            list[dict]: A list of dictionaries containing metadata for each variable
            in the series. Each dictionary includes the following keys:
                - "id_variable" (str): The ID of the variable.
                - "name_variable" (str): The name of the variable.
                - "id_value" (str): The ID of the value.
                - "name_variable" (str): The name of the variable (duplicated key).
        """
        response = self.client.get_valores_serie(cod_serie, det=1, tip="")
        data = self.__get_data_from_response(response)
        metadata = [
            {
                "id_variable": variable["Variable"]["Id"],
                "name_variable": variable["Variable"]["Nombre"],
                "id_value": variable["Id"],
                "name_value": variable["Nombre"],
            }
            for variable in data
        ]
        return metadata

    def get_data_serie(self, cod_serie: str, nult: int = None, date: str = None):
        """
        Retrieves data from a specific series using its ID.

        Args:
            cod_serie (str): The identifier of the series to retrieve data from.
            nult (int, optional): The number of most recent data points to retrieve. Defaults to 1.
            date (str, optional): A date range filter for the data in the format "aaaammdd:aaaammdd". Defaults to None.

        Returns:
            list: A list of dictionaries containing the series data.

        """

        response = self.client.get_datos_serie(cod_serie, nult=nult, date=date, det=2, tip="")
        data = self.__get_data_from_response(response)
        data = [
            {"cod_serie": data["COD"], "name_serie": data["Nombre"], "unidad": data["Unidad"].get("Nombre")}
            | {
                "type_data": values["TipoDato"].get("Nombre"),
                "timestamp": pd.to_datetime(values["Fecha"], unit="ms"),
                "period": values["Periodo"],
                "year": values["Anyo"],
                "value": values["Valor"],
            }
            for values in data["Data"]
        ]
        return data

    def get_data_operation(self, cod_operation: str, filters: List[str], p: int, date: str = None, nult: int = 1):
        """
        Retrieves data from a specific operation based on the provided parameters.

        Args:
            cod_operation (str): The identifier of the operation to fetch data for.
            date (str, optional): A date range filter for the data in the format "aaaammdd:aaaammdd". Defaults to None.
            p (int): The periodicity of the data to retrieve.
            nult (int, optional): The number of most recent data points to retrieve. Defaults to 1.
            filters (List, optional): A list of filters to apply to the data retrieval. Defaults to an empty list.

        Returns:
            List[Dict]: A list of dictionaries containing the retrieved data.

        """

        response = self.client.get_datos_metadata_operacion(
            cod_operation, filters=filters, p=p, nult=nult, date=date, det=2, tip=""
        )
        data = self.__get_data_from_response(response)
        data = [
            {
                "cod_operation": cod_operation,
                "cod_serie": item["COD"],
                "name_serie": item["Nombre"],
                "unidad": item["Unidad"].get("Nombre"),
                "periodicity": self.periodicities[p],
                "type_data": values["TipoDato"].get("Nombre"),
                "timestamp": pd.to_datetime(values["Fecha"], unit="ms"),
                "period": values["Periodo"],
                "year": values["Anyo"],
                "Value": values["Valor"],
            }
            for item in data
            for values in item["Data"]
        ]
        return data

    def get_data_table(self, id_table: str, nult: int = 1, date: str = None, filters: List = None):
        """
        Retrieves data from a specified table using the provided table ID, number of last entries,
        and optional filters.

        Args:
            id_table (str): The ID of the table to retrieve data from.
            nult (int, optional): The number of most recent entries to retrieve. Defaults to 1.
            date (str, optional): A date range filter for the data in the format "aaaammdd:aaaammdd". Defaults to None.
            filters (List[str], optional): A list of filters to apply to the data retrieval.

        Returns:
            List[Dict]: A list of dictionaries containing the retrieved data.

        """

        response = self.client.get_datos_tabla(id_table, nult=nult, det=2, date=date, tip="", filters=filters)
        data = self.__get_data_from_response(response)

        data = [
            {
                "cod_table": item["COD"],
                "name_table": item["Nombre"],
                "unidad": item["Unidad"].get("Nombre"),
                "type_data": values["TipoDato"].get("Nombre"),
                "timestamp": pd.to_datetime(values["Fecha"], unit="ms"),
                "period": values["Periodo"],
                "year": values["Anyo"],
                "value": values["Valor"],
            }
            for item in data
            for values in item["Data"]
        ]
        return data

    @staticmethod
    def filter_series_by_metadata(series, filters):
        """
        Filters a list of series based on metadata criteria.

        This method allows filtering series by matching specific variable-value pairs in their metadata.
        Each filter should be provided in the format "id_variable:id_value".

        Args:
            series (List[Dict]): List of series to filter, where each series contains a 'metadata' field
                               with variable-value pairs.
            filters (List[str]): List of filters in the format "id_variable:id_value". If id_value is empty,
                               it will match any value for the given variable.

        Returns:
            List[Dict]: Filtered list of series that match all the provided criteria.

        """
        series_with_filters = series
        for filter in filters:
            id_variable, id_value = filter.split(":")
            condition_variable = lambda metadata: str(metadata["id_variable"] == str(id_variable))
            condition_value = lambda metadata: (str(metadata["id_value"]) == str(id_value))

            series_with_filters = [
                serie
                for serie in series_with_filters
                if max(
                    [
                        condition_variable(metadata) and (condition_value(metadata) if id_value != "" else True)
                        for metadata in serie["metadata"]
                    ]
                )
            ]
        return series_with_filters
