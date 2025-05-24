const CHANGE_EVENT_PREFIX = 'change:';

export class SocketModel {
  socket_: any;
  attachListeners_: any = [];
  nameListeners_: Map<string, any> = new Map();

  attach(socket: any) {
    this.socket_ = socket;
    this.attachListeners_.forEach((func: any) => {
      func(this);
    });
  }

  detach() {
    this.socket_ = null;
  }

  onAttach(func: any) {
    this.attachListeners_.push(func);
    if (!!this.socket_) {
      func(this);
    }
  }

  // Doesn't support get() - this is for compatibility with jupyter widget model
  get() {
    return null;
  }

  fetch(name: string) {
    return new Promise((resolve) => {
      this.socket_.emit('get:' + name, (data: any) => {
        resolve(data);
      });
    });
  }

  set(name: string, value: any) {
    if (!this.socket_) return;
    this.socket_.emit('set:' + name, value);

    // Check if there are other handlers for this name. We can update them
    // without even going through the socket
    if (this.nameListeners_.has(name))
      this.nameListeners_.get(name).forEach((f: any) => f(this, value));
  }

  // Do nothing - this is for compatibility with jupyter widget model
  save_changes() {}

  on(eventName: string, func: any) {
    if (!this.socket_) {
      this.onAttach(() => this.on(eventName, func));
      return;
    }
    if (eventName.startsWith(CHANGE_EVENT_PREFIX)) {
      let propName = eventName.slice(CHANGE_EVENT_PREFIX.length);
      if (!this.nameListeners_.has(propName))
        this.nameListeners_.set(propName, []);
      this.nameListeners_.get(propName).push(func);
      this.socket_.on(eventName, (val: any) => func(this, val));
    } else {
      console.error(
        `Tried to register an unsupported event '${eventName}' with SocketModel. Only events starting with '${CHANGE_EVENT_PREFIX}' are supported.`
      );
    }
  }
}
