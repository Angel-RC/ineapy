import inspect
import re
from typing import Any, Dict, List, Optional, Union

from dlt.sources.helpers.rest_client import RESTClient
from dlt.sources.helpers.rest_client.paginators import PageNumberPaginator
from requests import Response


class INEWrapper:
    """
    Wrapper for the INE (National Statistics Institute) API.

    This class implements an interface to access information available in INEbase
    through URL requests with the structure:
    https://servicios.ine.es/wstempus/js/{language}/{function}/{input}[?parameters]

    Required fields are:
    - {language}: ES (Spanish) or EN (English)
    - {function}: Specific API function
    - {input}: Input identifiers according to the function

    Optional parameters are set with ? and separated with &
    """

    def __init__(self, language: str = "ES"):
        """
        Initializes the INE API wrapper.

        Args:
            base_url (str): Base URL of the INE API. Default is the official URL.
        """
        self.base_url = f"https://servicios.ine.es/wstempus/js/{language}/"
        self.client = RESTClient(base_url=self.base_url, paginator=PageNumberPaginator(base_page=1, total_path=None))
        self.periodicities = self.get_periodicidades().json()
        self.periodicities = [item["Id"] for item in self.periodicities]

    @staticmethod
    def __solve_errors_in_response(response, *args, **kargs):
        content_text = response.content.decode("utf-8")
        clean_content_text = content_text.replace("\n", "")
        if clean_content_text.startswith("[") and not clean_content_text.endswith("]"):
            response._content = response.content + "]".encode("utf-8")
        return response

    @staticmethod
    def __validate_detalle(det: int) -> None:
        """Validates the detail level."""
        if not isinstance(det, int) or det not in (0, 1, 2):
            raise Exception("Bad param: Detail level (det) must be 0, 1 or 2")

    @staticmethod
    def __validate_tipo(tip: str) -> None:
        """Validates the response type."""
        if tip not in ("", "A", "M", "AM"):
            raise Exception("Bad param: Response type (tip) must be '', 'A', 'M' or 'AM'")

    @staticmethod
    def __validate_date(date: str) -> None:
        """Validates the date format."""
        if not re.match(r"^\d{8}:\d{8}$", date):
            raise Exception("Bad param: Date format must be 'yyyymmdd:yyyymmdd'")

        start_date, end_date = date.split(":")
        if int(start_date) > int(end_date):
            raise Exception("Bad param: Start date must be before end date")

    @staticmethod
    def __validate_nult(nult: int) -> None:
        """Validates the number of last data points."""
        if not isinstance(nult, int) or nult <= 0:
            raise Exception("Bad param: Number of last data points (nult) must be a positive integer")

    @staticmethod
    def __validate_geo(geo: int) -> None:
        """Validates the geo parameter."""
        if geo not in (0, 1):
            raise Exception("Bad param: Geo parameter must be 0 (national) or 1 (autonomous communities)")

    def __validate_periodicidad(self, p: int) -> None:
        """Validates the periodicity."""
        if not isinstance(p, int) or p not in self.periodicities:
            raise Exception(f"Bad param: Periodicity must be one of the following values: {self.periodicities}")

    @staticmethod
    def __validate_nult_date(nult: Optional[int], date: Optional[str]) -> None:
        """Validates that at least one of nult or date is not None."""
        if nult is None and date is None:
            raise Exception("Bad param: Either nult or date must be specified")

    @staticmethod
    def __validate_filters(filters: List[str]) -> None:
        """Validates the filters."""
        for filter in filters:
            if not isinstance(filter, str):
                raise Exception("Bad param: Filters must be a list of strings")

            # Validar con expresión regular que el formato sea dígitos:dígitos o dígitos:
            if not re.match(r"^\d+:(\d+)?$", filter):
                raise Exception(
                    f"Bad param: Filter '{filter}' must have format 'id_variable:id_value' or 'id_variable:'"
                )

    @staticmethod
    def __validate_params(func):
        """
        Decorator that automatically validates function parameters.

        Args:
            func: Function to decorate

        Returns:
            Function decorated with parameter validation
        """

        def wrapper(self, *args, **kwargs):
            # Get function parameter names
            sig = inspect.signature(func)
            bound_args = sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()

            # Validate each parameter according to its name
            for name, value in bound_args.arguments.items():
                if value is None:
                    continue

                elif name == "det":
                    self.__validate_detalle(value)
                elif name == "tip":
                    self.__validate_tipo(value)
                elif name == "nult":
                    self.__validate_nult(value)
                elif name == "date":
                    self.__validate_date(value)
                elif name == "geo":
                    self.__validate_geo(value)
                elif name == "p":
                    self.__validate_periodicidad(value)
                elif name == "filters":
                    self.__validate_filters(value)

            # Validate nult and date if both are present in the function signature
            if "nult" in bound_args.arguments and "date" in bound_args.arguments:
                self.__validate_nult_date(bound_args.arguments["nult"], bound_args.arguments["date"])

            return func(self, *args, **kwargs)

        return wrapper

    # Operations Endpoints -------------------------------------------------
    @__validate_params
    def get_operacion(self, cod_operation: str, det: int = 0, tip: str = "M") -> Response:
        """
        Retrieves detailed information about a statistical operation.

        Args:
            cod_operation (str): Operation identifier code
            det (int): Detail level (0, 1 or 2)
            tip (str): Response type:
                      - "": normal response
                      - "A": friendly response
                      - "M": include metadata
                      - "AM": friendly with metadata

        Returns:
            Dict[str, Any]: Operation information including its identifier,
                           name, code and other details according to the requested level

        Raises:
            Exception: If any parameter is invalid
        """
        response = self.client.get(f"/OPERACION/{cod_operation}", params={"det": det, "tip": tip})
        return response

    @__validate_params
    def get_operaciones_disponibles(self, det: int = 0, tip: str = "", geo: Optional[int] = None) -> Response:
        """
        Retrieves the list of available operations.

        Args:
            det (int): Detail level (0, 1 or 2)
            tip (str): Response type:
                      - "": normal response
                      - "A": friendly response
                      - "M": include metadata
                      - "AM": friendly with metadata
            geo (Optional[int]): 0 for national results, 1 for autonomous communities

        Returns:
            List[Dict[str, Any]]: List of available operations

        Raises:
            Exception: If any parameter is invalid
        """
        params = {"det": det, "tip": tip}
        if geo is not None:
            params["geo"] = geo

        response = self.client.get("/OPERACIONES_DISPONIBLES", params=params)
        return response

    # Series Endpoints -----------------------------------------------------
    @__validate_params
    def get_serie(self, cod_serie: str, det: int = 0, tip: str = "M") -> Response:
        """
        Retrieves information about a specific series.

        Args:
            cod_serie (str): Series code
            det (int): Detail level (0-2)
            tip (str): Response type ("A", "M", "AM")

        Returns:
            Dict[str, Any]: Series information

        Raises:
            Exception: If any parameter is invalid
        """
        response = self.client.get(f"/SERIE/{cod_serie}", params={"det": det, "tip": tip})
        return response

    @__validate_params
    def get_datos_serie(
        self, cod_serie: str, nult: Optional[int] = None, date: Optional[str] = None, det: int = 0, tip: str = ""
    ) -> Response:
        """
        Retrieves values and metadata of a time series.

        Args:
            cod_serie (str): Series identifier code
            nult (Optional[int]): Number of last data points to retrieve
            date (Optional[str]): Date range in format "yyyymmdd:yyyymmdd"
            det (int): Detail level (0, 1 or 2)
            tip (str): Response type ("", "A", "M", "AM")

        Returns:
            Dict[str, Any]: Series data including values, dates,
                           and metadata according to the requested detail level

        Raises:
            Exception: If any parameter is invalid or if both nult and date are None
        """
        params = {"det": det, "tip": tip, "nult": nult, "date": date}

        response = self.client.get(f"/DATOS_SERIE/{cod_serie}", params=params)
        return response

    @__validate_params
    def get_series_operacion(
        self,
        cod_operation: str,
        det: int = 0,
        tip: str = "M",
        page: Optional[int] = None,
    ) -> Response:
        """
        Retrieves the series associated with a statistical operation limited to a specific page.

        Args:
            cod_operation (str): Statistical operation identifier code
            det (int): Detail level:
                      - 0: Basic information
                      - 1: Basic information + metadata
                      - 2: Complete information
            tip (str): Response type:
                      - "": Normal response
                      - "A": Friendly response
                      - "M": Include metadata
                      - "AM": Friendly with metadata
            page (Optional[int]): Page number to retrieve. If None, returns the first page.

        Returns:
            Dict[str, Any]: Response object containing the series from the requested page

        Raises:
            Exception: If any parameter is invalid
        """
        params = {"det": det, "tip": tip, "page": page}

        response = self.client.get(f"/SERIES_OPERACION/{cod_operation}", params=params)
        return response

    @__validate_params
    def get_series_operacion_all_pages(
        self,
        cod_operation: str,
        det: int = 0,
        tip: str = "M",
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all series associated with a statistical operation by fetching all available pages.

        Args:
            cod_operation (str): Statistical operation identifier code
            det (int): Detail level:
                      - 0: Basic information
                      - 1: Basic information + metadata
                      - 2: Complete information
            tip (str): Response type:
                      - "": Normal response
                      - "A": Friendly response
                      - "M": Include metadata
                      - "AM": Friendly with metadata

        Returns:
            List[Dict[str, Any]]: List containing all series from all available pages

        Raises:
            Exception: If any parameter is invalid
        """
        params = {"det": det, "tip": tip}

        data = []
        for page in self.client.paginate(
            f"/SERIES_OPERACION/{cod_operation}", params=params, hooks={"response": self.__solve_errors_in_response}
        ):
            data += [page.response]
        return data

    # Tables Endpoints -----------------------------------------------------
    @__validate_params
    def get_tabla(self, id_table: str, det: int = 0, tip: str = "M") -> Response:
        """
        Retrieves information about a specific table.

        Args:
            id_table (str): Table ID
            det (int): Detail level (0-2)
            tip (str): Response type ("", "A", "M", "AM")

        Returns:
            Dict[str, Any]: Table information

        Raises:
            Exception: If any parameter is invalid
        """
        response = self.client.get(f"/TABLA/{id_table}", params={"det": det, "tip": tip})
        return response

    @__validate_params
    def get_datos_tabla(
        self,
        id_table: str,
        nult: Optional[int] = None,
        date: Optional[str] = None,
        det: int = 0,
        tip: str = "",
        filters: Optional[List[str]] = None,
    ) -> Response:
        """
        Retrieves data from a specific table.

        Args:
            id_table (str): Table ID
            nult (Optional[int]): Number of last data points to retrieve
            det (int): Detail level (0-2)
            tip (str): Response type ("", "A", "M", "AM")
            filters (Optional[List[str]]): List of filters to apply. Each filter should be a string
                                         in the format "id_variable:id_value" or "id_variable:"
        Returns:
            Dict[str, Any]: Table data

        Raises:
            Exception: If any parameter is invalid
        """
        params = {"det": det, "tip": tip, "nult": nult, "date": date}
        filter_string = f"?{'&'.join(f'tv={f}' for f in filters)}" if filters else ""

        response = self.client.get(f"/DATOS_TABLA/{id_table}{filter_string}", params=params)
        return response

    # Variables Endpoints -------------------------------------------------
    @__validate_params
    def get_variables(self, det: int = 0, tip: str = "") -> Response:
        """
        Retrieves the complete list of variables available in the system.

        Args:
            det (int): Detail level (0, 1 or 2)
            tip (str): Response type ("", "A", "M", "AM")

        Returns:
            List[Dict[str, Any]]: List of variables with their identifiers and names

        Raises:
            Exception: If any parameter is invalid
        """
        response = self.client.get("/VARIABLES", params={"det": det, "tip": tip})
        return response

    @__validate_params
    def get_valores_variable(self, id_variable: str, det: int = 1, tip: str = "M") -> Response:
        """
        Retrieves possible values of a variable.

        Args:
            id_variable (str): Variable ID
            det (int): Detail level (0-2)
            tip (str): Response type ("", "A", "M", "AM")

        Returns:
            List[Dict[str, Any]]: List of values

        Raises:
            Exception: If any parameter is invalid
        """
        response = self.client.get(f"/VALORES_VARIABLE/{id_variable}", params={"det": det, "tip": tip})
        return response

    # Periodicities Endpoints --------------------------------------------
    def get_periodicidades(self) -> Response:
        """
        Retrieves the list of periodicities available in the system.

        Returns:
            List[Dict[str, Any]]: List of periodicities with their identifiers,
                                 names and codes
        """
        response = self.client.get("/PERIODICIDADES")
        return response

    # Groups Endpoints ---------------------------------------------------
    @__validate_params
    def get_grupos_tabla(self, id_table: str, det: int = 0, tip: str = "M") -> Response:
        """
        Retrieves groups of a table.

        Args:
            id_table (str): Table ID
            det (int): Detail level (0-2)
            tip (str): Response type ("", "A", "M", "AM")

        Returns:
            List[Dict[str, Any]]: List of groups

        Raises:
            Exception: If any parameter is invalid
        """
        response = self.client.get(f"/GRUPOS_TABLA/{id_table}", params={"det": det, "tip": tip})
        return response

    @__validate_params
    def get_valores_grupos_tabla(self, id_table: str, id_grupo: str, det: int = 1, tip: str = "A") -> Response:
        """
        Retrieves values of a table group.

        Args:
            id_table (str): Table ID
            id_grupo (str): Group ID
            det (int): Detail level (0-2)
            tip (str): Response type ("", "A", "M", "AM")

        Returns:
            List[Dict[str, Any]]: List of values

        Raises:
            Exception: If any parameter is invalid
        """
        response = self.client.get(f"/VALORES_GRUPOSTABLA/{id_table}/{id_grupo}", params={"det": det, "tip": tip})
        return response

    # Variables and Values Endpoints -----------------------------------------
    @__validate_params
    def get_variables_operacion(self, cod_operation: str, det: int = 1, tip: str = "A") -> Response:
        """
        Retrieves variables associated with a specific operation.

        Args:
            cod_operation (str): Operation identifier code
            det (int): Detail level (0, 1 or 2)
            tip (str): Response type ("", "A", "M", "AM")

        Returns:
            List[Dict[str, Any]]: List of variables associated with the operation

        Raises:
            Exception: If any parameter is invalid
        """
        response = self.client.get(f"/VARIABLES_OPERACION/{cod_operation}", params={"det": det, "tip": tip})
        return response

    @__validate_params
    def get_valores_variable_operacion(
        self, id_variable: str, cod_operation: str, det: int = 0, tip: str = "AM"
    ) -> Response:
        """
        Retrieves values of a variable for a specific operation.

        Args:
            id_variable (str): Variable identifier
            cod_operation (str): Operation identifier code
            det (int): Detail level (0, 1 or 2)
            tip (str): Response type ("", "A", "M", "AM")

        Returns:
            List[Dict[str, Any]]: List of possible values for the variable
                                 in the specified operation

        Raises:
            Exception: If any parameter is invalid
        """
        response = self.client.get(
            f"/VALORES_VARIABLEOPERACION/{id_variable}/{cod_operation}", params={"det": det, "tip": tip}
        )
        return response

    # Series by Metadata Endpoints ---------------------------------------
    @__validate_params
    def get_serie_metadata_operacion(
        self,
        cod_operation: str,
        filters: List[str],
        p: int = None,
        page: int = None,
        det: int = 0,
        tip: str = "",
    ) -> Response:
        """
        Retrieves series of an operation that meet certain metadata criteria limited to a specific page.

        Args:
            cod_operation (str): Operation identifier code
            filters (List[str]): List of metadata filters in the format "id_variable:id_value" or "id_variable:"
            p (Optional[int]): Periodicity. If not specified, all available data is returned.
            page (Optional[int]): Page number to retrieve. If None, returns the first page.
            det (int): Detail level:
                      - 0: Basic information
                      - 1: Basic information + metadata
                      - 2: Complete information
            tip (str): Response type:
                      - "": Normal response
                      - "A": Friendly response
                      - "M": Include metadata
                      - "AM": Friendly with metadata

        Returns:
            Dict[str, Any]: Response object containing the series from the requested page that meet the specified criteria

        Raises:
            Exception: If any parameter is invalid
        """
        params = {"det": det, "tip": tip, "p": p, "page": page}
        filters = {f"g{i + 1}": value for i, value in enumerate(filters)}
        params = params | filters

        response = self.client.get(f"/SERIE_METADATAOPERACION/{cod_operation}", params=params)
        return response

    @__validate_params
    def get_serie_metadata_operacion_all_pages(
        self,
        cod_operation: str,
        filters: List[str],
        p: int = None,
        det: int = 0,
        tip: str = "M",
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all series of an operation that meet certain metadata criteria by fetching all available pages.

        Args:
            cod_operation (str): Operation identifier code
            filters (List[str]): List of metadata filters in the format "id_variable:id_value" or "id_variable:"
            p (Optional[int]): Periodicity. If not specified, all available data is returned.
            det (int): Detail level:
                      - 0: Basic information
                      - 1: Basic information + metadata
                      - 2: Complete information
            tip (str): Response type:
                      - "": Normal response
                      - "A": Friendly response
                      - "M": Include metadata
                      - "AM": Friendly with metadata

        Returns:
            List[Dict[str, Any]]: List containing all series from all available pages that meet the specified criteria

        Raises:
            Exception: If any parameter is invalid
        """
        params = {"det": det, "tip": tip, "p": p}
        filters = {f"g{i + 1}": value for i, value in enumerate(filters)}
        params = params | filters

        data = []
        for page in self.client.paginate(
            f"/SERIE_METADATAOPERACION/{cod_operation}",
            params=params,
            hooks={"response": [self.__solve_errors_in_response]},
        ):
            data += [page.response]
        return data

    @__validate_params
    def get_datos_metadata_operacion(
        self,
        cod_operation: str,
        filters: List[str],
        p: int,
        nult: Optional[int] = None,
        date: Optional[str] = None,
        det: int = 2,
        tip: str = "",
    ) -> Response:
        """
        Retrieves data from series of an operation that meet metadata criteria.

        This endpoint allows obtaining data from time series associated with a statistical operation
        that meet certain metadata criteria specified through filters.

        Args:
            cod_operation (str): Statistical operation identifier code
            nult (Optional[int]): Number of last data points to retrieve. If not specified,
                                all available data is returned.
            p (int): Periodicity. If not specified, all available data is returned.
            det (int): Detail level:
                      - 0: Basic information
                      - 1: Basic information + metadata
                      - 2: Complete information
            date (Optional[str]): Date range in format "aaaammdd:aaaammdd". If not specified,
            tip (str): Response type:
                      - "": Normal response
                      - "A": Friendly response
                      - "M": Include metadata
                      - "AM": Friendly with metadata
            filters (Optional[List[str]]): List of metadata filters. Each filter must have
                                         the format "id_variable:id_value". For example:
                                         ["115:1", "116:2"] to filter by two variables.

        Returns:
            Dict[str, Any]: Data from series that meet the specified criteria.

        """
        params = {"det": det, "tip": tip, "p": p, "nult": nult, "date": date}
        filters = {f"g{i + 1}": value for i, value in enumerate(filters)}
        params = params | filters

        response = self.client.get(f"/DATOS_METADATAOPERACION/{cod_operation}", params=params)

        return response

    @__validate_params
    def get_series_tabla(
        self,
        id_table: str,
        det: int = 0,
        tip: str = "M",
        filters: Optional[List[str]] = None,
    ) -> Response:
        """
        Retrieves series associated with a specific table.

        This endpoint allows obtaining time series that are part of a statistical table,
        with the possibility of applying additional filters.

        Args:
            id_table (str): Table identifier code
            det (int): Detail level:
                      - 0: Basic information
                      - 1: Basic information + metadata
                      - 2: Complete information
            tip (str): Response type:
                      - "": Normal response
                      - "A": Friendly response
                      - "M": Include metadata
                      - "AM": Friendly with metadata
            filters (Optional[List[str]]): List of filters to apply. Each filter should be a string
                                         in the format "variable_id:value_id"

        Returns:
            List[Dict[str, Any]]: List of series associated with the table

        Raises:
            Exception: If any parameter is invalid
        """
        params = {"det": det, "tip": tip}
        filter_string = f"?{'&'.join(f'tv={f}' for f in filters)}" if filters else ""

        response = self.client.get(f"/SERIES_TABLA/{id_table}{filter_string}", params=params)
        return response

    @__validate_params
    def get_valores_serie(self, cod_serie: str, det: int = 0, tip: str = "M") -> Response:
        """
        Retrieves values of a time series.

        This endpoint allows obtaining historical values of a specific time series,
        including its metadata and characteristics.

        Args:
            cod_serie (str): Series identifier code
            det (int): Detail level:
                      - 0: Basic information
                      - 1: Basic information + metadata
                      - 2: Complete information
            tip (str): Response type:
                      - "": Normal response
                      - "A": Friendly response
                      - "M": Include metadata
                      - "AM": Friendly with metadata

        Returns:
            List[Dict[str, Any]]: List of series values.

        Raises:
            Exception: If any parameter is invalid
        """
        response = self.client.get(f"/VALORES_SERIE/{cod_serie}", params={"det": det, "tip": tip})
        return response

    # Publications Endpoints ---------------------------------------------
    @__validate_params
    def get_publicaciones(self, det: int = 0, tip: str = "") -> Response:
        """
        Retrieves the list of available publications.

        Args:
            det (int): Detail level (0, 1 or 2)
            tip (str): Response type ("", "A", "M", "AM")

        Returns:
            List[Dict[str, Any]]: List of publications with their identifiers,
                                 names and metadata according to the detail level

        Raises:
            Exception: If any parameter is invalid
        """
        response = self.client.get("/PUBLICACIONES", params={"det": det, "tip": tip})
        return response

    # Tables by Operation Endpoints -----------------------------------------
    @__validate_params
    def get_tablas_operacion(self, cod_operation: str, det: int = 2, tip: str = "M") -> Response:
        """
        Retrieves tables associated with a specific operation.

        Args:
            cod_operation (str): Operation identifier code
            det (int): Detail level (0, 1 or 2)
            tip (str): Response type ("", "A", "M", "AM")

        Returns:
            List[Dict[str, Any]]: List of tables associated with the operation

        Raises:
            Exception: If any parameter is invalid
        """
        response = self.client.get(f"/TABLAS_OPERACION/{cod_operation}", params={"det": det, "tip": tip})
        return response

    @__validate_params
    def get_publicaciones_operacion(self, cod_operation: str, det: int = 0, tip: str = "M") -> Response:
        """
        Retrieves publications associated with a statistical operation.

        This endpoint allows obtaining the list of publications related to a specific
        statistical operation, including their metadata and characteristics.

        Args:
            cod_operation (str): Operation identifier code
            det (int): Level of detail:
                      - 0: Basic information
                      - 1: Basic information + metadata
                      - 2: Complete information
            tip (str): Response type:
                      - "": Normal response
                      - "A": Friendly response
                      - "M": Include metadata
                      - "AM": Friendly with metadata

        Returns:
            List[Dict[str, Any]]: List of publications associated with the operation

        Raises:
            Exception: If any parameter is invalid
        """
        response = self.client.get(f"/PUBLICACIONES_OPERACION/{cod_operation}", params={"det": det, "tip": tip})
        return response

    @__validate_params
    def get_publicacion_fecha_publicacion(self, id_publicacion: str, det: int = 0, tip: str = "M") -> Response:
        """
        Retrieves the publication date of a specific publication.

        This endpoint allows obtaining the publication date and other metadata
        related to a specific INE publication.

        Args:
            id_publicacion (str): Publication identifier code
            det (int): Level of detail:
                      - 0: Basic information
                      - 1: Basic information + metadata
                      - 2: Complete information
            tip (str): Response type:
                      - "": Normal response
                      - "A": Friendly response
                      - "M": Include metadata
                      - "AM": Friendly with metadata

        Returns:
            Dict[str, Any]: Information about the publication date and metadata

        Raises:
            Exception: If any parameter is invalid
        """
        response = self.client.get(f"/PUBLICACIONFECHA_PUBLICACION/{id_publicacion}", params={"det": det, "tip": tip})
        return response
