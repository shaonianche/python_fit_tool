Split generated message construction into explicit create (`MessageClass()`)
and decode (`MessageClass.from_definition(...)`) paths; MessageFactory uses the
definition factory.
