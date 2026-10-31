from dify_plugin import DifyPluginEnv, Plugin

# Crawls and batches wait for results, so allow longer tool calls than the default.
plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=300))

if __name__ == "__main__":
    plugin.run()
